"""
The fan-out, against a real SSH server.

The API tests cover what a job may ask for; these cover what actually happens to
each node once it is asked — including the nodes that cannot be reached.
"""

import pytest
from asgiref.sync import sync_to_async

from fleet.models import FleetJob, FleetJobTask
from fleet.tasks import _fan_out, _finalize
from fleet.tests.factories import create_node, create_tenant
from fleet.tests.sshd import fleet_settings

pytestmark = pytest.mark.django_db


@sync_to_async
def make_job(nodes, action="uptime", status=FleetJob.STATUS.RUNNING):
    tenant = nodes[0].tenant
    job = FleetJob.objects.create(tenant=tenant, action=action, status=status)
    FleetJobTask.objects.bulk_create(FleetJobTask(job=job, node=node, node_code=node.code) for node in nodes)
    return job


@sync_to_async
def rows(job):
    return {task.node_code: task for task in job.tasks.all()}


@sync_to_async
def make_nodes(count, **overrides):
    tenant = create_tenant()
    return [create_node(tenant=tenant, **overrides) for _ in range(count)]


async def test_every_node_gets_its_own_result(sshd, client_key):
    port, _ = sshd
    _, key_path = client_key
    nodes = await make_nodes(3)
    job = await make_job(nodes)

    with fleet_settings(port, key_path):
        await _fan_out(job, "uptime", 10, None)

    tasks = await rows(job)
    assert len(tasks) == 3
    for node in nodes:
        task = tasks[node.code]
        assert task.status == FleetJobTask.STATUS.DONE
        assert task.exit_code == 0
        assert "ran:uptime" in task.stdout
        assert task.started_at and task.finished_at


async def test_a_non_zero_exit_fails_only_that_node(sshd, client_key):
    port, _ = sshd
    _, key_path = client_key
    nodes = await make_nodes(2)
    job = await make_job(nodes)

    with fleet_settings(port, key_path):
        await _fan_out(job, "fail", 10, None)

    for task in (await rows(job)).values():
        assert task.status == FleetJobTask.STATUS.FAILED
        assert task.exit_code == 3
        assert "nope" in task.stderr


async def test_an_unenrolled_node_is_skipped_not_omitted(sshd, client_key):
    port, _ = sshd
    _, key_path = client_key
    tenant = await sync_to_async(create_tenant)()
    reachable = await sync_to_async(create_node)(tenant=tenant)
    stranded = await sync_to_async(create_node)(tenant=tenant, mesh_ip=None)
    job = await make_job([reachable, stranded])

    with fleet_settings(port, key_path):
        await _fan_out(job, "uptime", 10, None)

    tasks = await rows(job)
    assert tasks[reachable.code].status == FleetJobTask.STATUS.DONE
    assert tasks[stranded.code].status == FleetJobTask.STATUS.SKIPPED
    assert "not enrolled" in tasks[stranded.code].error
    assert tasks[stranded.code].started_at is None


async def test_an_unreachable_node_records_why(client_key):
    _, key_path = client_key
    # Port 1 with nothing listening: a real connection failure, not a mock.
    nodes = await make_nodes(1)
    job = await make_job(nodes)

    with fleet_settings(1, key_path, FLEET_SSH_CONNECT_TIMEOUT=2):
        await _fan_out(job, "uptime", 5, None)

    task = (await rows(job))[nodes[0].code]
    assert task.status == FleetJobTask.STATUS.FAILED
    assert "Cannot reach" in task.error


async def test_a_cancelled_job_stops_reaching_nodes(sshd, client_key):
    port, _ = sshd
    _, key_path = client_key
    nodes = await make_nodes(3)
    job = await make_job(nodes, status=FleetJob.STATUS.CANCELLED)

    with fleet_settings(port, key_path):
        await _fan_out(job, "uptime", 10, None)

    for task in (await rows(job)).values():
        assert task.status == FleetJobTask.STATUS.CANCELLED
        assert task.started_at is None, "a cancelled node was never dialled"


async def test_output_is_truncated(sshd, client_key):
    port, _ = sshd
    _, key_path = client_key
    nodes = await make_nodes(1)
    job = await make_job(nodes)

    with fleet_settings(port, key_path, FLEET_JOB_OUTPUT_LIMIT=8):
        await _fan_out(job, "uptime", 10, None)

    task = (await rows(job))[nodes[0].code]
    assert task.stdout.startswith("ran:upti")
    assert "truncated" in task.stdout


async def test_finalize_writes_off_whatever_is_still_open():
    nodes = await make_nodes(2)
    job = await make_job(nodes)

    await sync_to_async(_finalize)(job)

    await sync_to_async(job.refresh_from_db)()
    assert job.status == FleetJob.STATUS.DONE
    assert job.finished_at
    for task in (await rows(job)).values():
        assert task.status == FleetJobTask.STATUS.FAILED
        assert "before this node was reached" in task.error


async def test_finalize_keeps_a_cancelled_job_cancelled():
    nodes = await make_nodes(1)
    job = await make_job(nodes, status=FleetJob.STATUS.CANCELLED)

    await sync_to_async(_finalize)(job)

    await sync_to_async(job.refresh_from_db)()
    assert job.status == FleetJob.STATUS.CANCELLED
    assert (await rows(job))[nodes[0].code].status == FleetJobTask.STATUS.CANCELLED

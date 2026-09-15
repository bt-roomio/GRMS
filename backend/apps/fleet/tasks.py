import asyncio
import logging

from celery import shared_task
from django.conf import settings

from core.utils.get_time import get_mil_sec
from fleet.actions import ACTIONS, build_command
from fleet.models import FleetAuditLog, FleetJob, FleetJobTask, FleetNode
from fleet.netbird.client import NetBirdClient
from fleet.netbird.exceptions import NetBirdError, NetBirdNotConfigured
from fleet.observables.fleet_node import publish_fleet_nodes
from fleet.utils import ssh
from fleet.utils.audit import alog_action, log_action
from fleet.utils.code import node_prefix
from fleet.utils.db import db
from fleet.utils.exceptions import FleetError, FleetNodeNotEnrolled
from fleet.utils.job import finish
from fleet.utils.time import to_mil_sec

logger = logging.getLogger(__name__)


def peer_name(peer) -> str:
    return peer.get("name") or ""


def apply_peer(node: FleetNode, peer: dict) -> bool:
    peer_id = peer.get("id")

    if node.netbird_peer_id and peer_id and node.netbird_peer_id != peer_id:
        logger.warning(
            "Peer id mismatch for %s: pinned=%s incoming=%s — ignoring",
            node.code,
            node.netbird_peer_id,
            peer_id,
        )
        log_action(
            FleetAuditLog.ACTION.PEER_MISMATCH,
            node=node,
            detail={
                "pinned": node.netbird_peer_id,
                "incoming": peer_id,
                "incoming_ip": peer.get("ip"),
            },
        )
        return False

    first_pin = not node.netbird_peer_id

    updates = {
        "netbird_peer_id": peer_id,
        "mesh_ip": peer.get("ip") or node.mesh_ip,
        "is_online": bool(peer.get("connected")),
        "last_seen": to_mil_sec(peer.get("last_seen")) or node.last_seen,
        "os": peer.get("os") or node.os,
        "netbird_version": peer.get("version") or node.netbird_version,
    }
    if first_pin:
        updates["enrolled_at"] = node.enrolled_at or get_mil_sec()

    changed = [field for field, value in updates.items() if getattr(node, field) != value]
    if not changed:
        return False

    for field, value in updates.items():
        setattr(node, field, value)
    node.save(update_fields=[*changed, "updated_at"])

    if first_pin:
        log_action(
            FleetAuditLog.ACTION.PEER_PINNED,
            node=node,
            detail={"peer_id": peer_id, "mesh_ip": node.mesh_ip},
        )

    return True


def sweep_unconfirmed(confirmed_ids) -> list:
    """
    Force offline every node this poll did not confirm as connected.

    The only fleet write that does not go through ``save()``: ``QuerySet.update()``
    is straight SQL, so no ``post_save`` fires and the repaint is published by hand.
    """
    stale = FleetNode.objects.is_active().filter(is_online=True).exclude(id__in=confirmed_ids)
    rows = list(stale.values_list("id", "tenant_id"))
    stale.update(is_online=False, updated_at=get_mil_sec())

    publish_fleet_nodes(tenant_id for _, tenant_id in rows)
    return [node_id for node_id, _ in rows]


@shared_task(name="fleet.tasks.poll_fleet_peers", ignore_result=True)
def poll_fleet_peers():
    try:
        client = NetBirdClient()
    except NetBirdNotConfigured:
        logger.debug("Fleet poller skipped: NetBird is not configured")
        return

    try:
        peers = client.list_peers(group_id=settings.NETBIRD_HOTEL_GROUP_ID or None)
    except NetBirdError:
        logger.exception("Fleet poller could not reach the NetBird API — leaving node status untouched")
        return

    prefix = f"{node_prefix()}_"
    by_code = {peer_name(peer): peer for peer in peers if peer_name(peer).startswith(prefix)}
    nodes = FleetNode.objects.is_active().filter(code__in=by_code.keys()) if by_code else []

    unmatched = set(by_code) - {node.code for node in nodes}
    if unmatched:
        logger.warning("Fleet poller saw %s peer(s) with no matching node: %s", len(unmatched), sorted(unmatched))

    touched, confirmed_ids = [], []
    for node in nodes:
        if apply_peer(node, by_code[node.code]):
            touched.append(node.id)
        if node.is_online:
            confirmed_ids.append(node.id)

    touched.extend(sweep_unconfirmed(confirmed_ids))

    logger.debug("Fleet poller: %s peers, %s nodes updated", len(peers), len(touched))


# --- Bulk jobs ---------------------------------------------------------------
#
# One Celery task per job, not per node: the fan-out happens inside a single
# event loop, a handful of nodes at a time, reusing the same `fleet.utils.ssh`
# the single-node endpoints use.


def _clip(text):
    """Keep one runaway node from filling the table with a log file."""
    limit = settings.FLEET_JOB_OUTPUT_LIMIT
    if text and len(text) > limit:
        return f"{text[:limit]}\n… truncated at {limit} characters"
    return text


@db
def _load_pending(job_id):
    return list(FleetJobTask.objects.filter(job_id=job_id, status=FleetJobTask.STATUS.PENDING).select_related("node"))


@db
def _job_status(job_id):
    return FleetJob.objects.filter(pk=job_id).values_list("status", flat=True).first()


@db
def _save_task(task, **fields):
    for field, value in fields.items():
        setattr(task, field, value)
    task.save(update_fields=list(fields))


async def _run_one(job, task, command, timeout, semaphore, user):
    async with semaphore:
        # The kill switch, checked once per node rather than once per batch: a
        # cancel lands on everything that has not been dialled yet.
        if await _job_status(job.id) == FleetJob.STATUS.CANCELLED:
            await _save_task(task, status=FleetJobTask.STATUS.CANCELLED, finished_at=get_mil_sec())
            return

        node = task.node
        if node is None or not node.mesh_ip:
            # Recorded, never silently omitted — a node that was not reached is
            # part of the result. Reachability is `mesh_ip`, the same thing
            # `ssh.connect` needs, so a job never refuses a node the single-node
            # endpoint would happily reach.
            await _save_task(
                task,
                status=FleetJobTask.STATUS.SKIPPED,
                error=f"{task.node_code} is not enrolled — it has no mesh IP yet.",
                finished_at=get_mil_sec(),
            )
            return

        started = get_mil_sec()
        await _save_task(task, status=FleetJobTask.STATUS.RUNNING, started_at=started)

        try:
            result = await ssh.run_command(node, command, timeout=timeout)
        except FleetError as exc:
            await _save_task(
                task,
                # Losing the mesh IP between the check above and the connection
                # is still "never reached", not "tried and failed".
                status=(
                    FleetJobTask.STATUS.SKIPPED if isinstance(exc, FleetNodeNotEnrolled) else FleetJobTask.STATUS.FAILED
                ),
                error=str(exc),
                finished_at=get_mil_sec(),
            )
            await alog_action(
                FleetAuditLog.ACTION.COMMAND_RUN,
                node=node,
                user=user,
                detail={"job_id": str(job.id), "action": job.action, "command": command, "error": str(exc)},
            )
            return

        rc = result["rc"]
        await _save_task(
            task,
            # A non-zero exit is a failed node, not a failed job: the other nodes
            # keep going and the rc is on the row.
            status=FleetJobTask.STATUS.DONE if rc == 0 else FleetJobTask.STATUS.FAILED,
            exit_code=rc,
            stdout=_clip(result["stdout"]),
            stderr=_clip(result["stderr"]),
            finished_at=get_mil_sec(),
        )
        await alog_action(
            FleetAuditLog.ACTION.COMMAND_RUN,
            node=node,
            user=user,
            detail={
                "job_id": str(job.id),
                "action": job.action,
                "command": command,
                "rc": rc,
                "duration_ms": get_mil_sec() - started,
            },
        )


async def _fan_out(job, command, timeout, user):
    tasks = await _load_pending(job.id)
    if not tasks:
        return

    semaphore = asyncio.Semaphore(max(1, settings.FLEET_JOB_CONCURRENCY))
    running = [_run_one(job, task, command, timeout, semaphore, user) for task in tasks]

    try:
        # A whole-job deadline. Without it a fleet of slow nodes outlives the
        # Celery time limit, which would kill the worker mid-write instead of
        # letting the job close its own books.
        await asyncio.wait_for(
            asyncio.gather(*running, return_exceptions=True),
            timeout=settings.FLEET_JOB_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "Fleet job %s hit its %ss budget — the rest is marked failed", job.id, settings.FLEET_JOB_TIMEOUT
        )


def _finalize(job, reason=None) -> None:
    """
    Close the books.

    Anything still open is written off here, so no task is left claiming to be
    running once the worker has moved on.
    """
    leftover = FleetJobTask.objects.filter(
        job_id=job.id,
        status__in=(FleetJobTask.STATUS.PENDING, FleetJobTask.STATUS.RUNNING),
    )

    job.refresh_from_db(fields=["status"])
    cancelled = job.status == FleetJob.STATUS.CANCELLED

    if cancelled:
        leftover.update(status=FleetJobTask.STATUS.CANCELLED, finished_at=get_mil_sec())
    else:
        leftover.update(
            status=FleetJobTask.STATUS.FAILED,
            error=reason or "The job ended before this node was reached.",
            finished_at=get_mil_sec(),
        )

    finish(job, job.status if cancelled else FleetJob.STATUS.DONE)


@shared_task(
    name="fleet.tasks.run_fleet_job",
    ignore_result=True,
    # The global 300s limit is sized for ordinary tasks; a fan-out over a fleet
    # needs its own budget, kept just above the job's internal deadline.
    soft_time_limit=settings.FLEET_JOB_TIMEOUT + 120,
    time_limit=settings.FLEET_JOB_TIMEOUT + 180,
)
def run_fleet_job(job_id):
    job = FleetJob.objects.filter(pk=job_id).first()
    if job is None:
        logger.warning("Fleet job %s no longer exists", job_id)
        return

    # `task_acks_late` means this can be redelivered after a worker dies. Only a
    # job still sitting at pending is ours to start; anything else is already
    # under way, cancelled, or finished.
    if job.status != FleetJob.STATUS.PENDING:
        logger.info("Fleet job %s is %s — not starting it again", job.id, job.status)
        return

    try:
        command = build_command(job.action, job.params)
    except FleetError as exc:
        # The API validates this before creating the job, so getting here means
        # the catalog changed underneath a queued job.
        logger.warning("Fleet job %s has an unusable action: %s", job.id, exc)
        _finalize(job, reason=str(exc))
        return

    job.status = FleetJob.STATUS.RUNNING
    job.started_at = get_mil_sec()
    job.save(update_fields=["status", "started_at", "updated_at"])

    timeout = (ACTIONS[job.action].timeout if job.action in ACTIONS else None) or settings.FLEET_SSH_COMMAND_TIMEOUT
    user = job.created_by

    try:
        ssh.run_blocking(lambda: _fan_out(job, command, timeout, user))
    finally:
        _finalize(job)

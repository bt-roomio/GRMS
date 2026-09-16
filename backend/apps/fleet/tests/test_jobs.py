"""The action catalog and the jobs API. The runner itself lives in test_job_runner."""

from unittest.mock import AsyncMock, patch

from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse

from core.tests.base import BaseTestCase
from fleet.actions import ACTIONS, ActionParam, FleetAction, FleetActionInvalidParams, FleetActionUnknown, get_action
from fleet.models import FleetAuditLog, FleetJob, FleetJobTask, FleetNode
from fleet.tasks import run_fleet_job
from fleet.tests.factories import create_gateway, create_node, create_tenant
from fleet.utils.code import node_prefix
from main.models import Tenant
from users.models import User

TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"
OTHER_TENANT_ID = "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc"

NODE_CODE = f"{node_prefix()}_jobs_1"
OTHER_CODE = f"{node_prefix()}_jobs_other_1"

# Defined here rather than picked out of the catalog: these cover what the
# machinery guarantees about *any* action, and must keep doing so however thin
# the shipped catalog gets.
FREE_FORM = FleetAction(
    name="echo_note",
    title="Echo",
    description="Only exists in this test.",
    template="echo {note}",
    params=(ActionParam(name="note", description="Anything", required=True),),
)

NO_PARAMS = FleetAction(
    name="plain",
    title="Plain",
    description="Only exists in this test.",
    template="true",
)

SERVICE_LOGS = FleetAction(
    name="service_logs",
    title="Service logs",
    description="Only exists in this test.",
    template="journalctl -u {gateway_service} -n {lines}",
    params=(
        ActionParam(
            name="lines",
            description="How many log lines to return.",
            default=200,
            choices=("50", "200"),
        ),
    ),
)


class ActionCatalogTest(BaseTestCase):
    """No database involved — this is the layer that decides what may run at all."""

    def test_an_unknown_action_is_refused(self):
        with self.assertRaises(FleetActionUnknown):
            get_action("rm_rf_slash")

    def test_a_param_the_action_does_not_declare_is_refused(self):
        with self.assertRaises(FleetActionInvalidParams):
            NO_PARAMS.build({"target": "/"})

    def test_a_server_side_value_cannot_be_supplied_by_the_caller(self):
        with self.assertRaises(FleetActionInvalidParams):
            SERVICE_LOGS.build({"gateway_service": "sshd"})

    def test_a_value_outside_the_choices_is_refused(self):
        with self.assertRaises(FleetActionInvalidParams):
            SERVICE_LOGS.build({"lines": "; rm -rf /"})

    def test_a_missing_required_param_is_refused(self):
        with self.assertRaises(FleetActionInvalidParams):
            FREE_FORM.build({})

    def test_free_text_reaches_the_shell_quoted(self):
        command = FREE_FORM.build({"note": "hi; rm -rf /"})
        self.assertEqual(command, "echo 'hi; rm -rf /'")

    def test_the_default_is_used_when_the_param_is_absent(self):
        self.assertIn("-n 200", SERVICE_LOGS.build({}))

    @override_settings(FLEET_GATEWAY_SERVICE="roomio-edge")
    def test_the_gateway_service_comes_from_settings(self):
        self.assertIn("roomio-edge", SERVICE_LOGS.build({}))


class FleetJobApiTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.tenant = Tenant.objects.get(pk=TENANT_ID)
        self.other_tenant = Tenant.objects.get(pk=OTHER_TENANT_ID)

        self.node = FleetNode.objects.create(
            tenant=self.tenant,
            gateway=create_gateway(self.tenant, name="Jobs Front Desk"),
            code=NODE_CODE,
            mesh_ip="100.84.90.52",
            netbird_peer_id="peer-1",
        )
        self.second_node = FleetNode.objects.create(
            tenant=self.tenant,
            gateway=create_gateway(self.tenant, name="Jobs Spa"),
            code=f"{NODE_CODE}_b",
            mesh_ip="100.84.90.53",
            netbird_peer_id="peer-2",
        )
        self.foreign_node = FleetNode.objects.create(
            tenant=self.other_tenant,
            gateway=create_gateway(self.other_tenant, name="Jobs Lobby"),
            code=OTHER_CODE,
            mesh_ip="100.84.90.54",
            netbird_peer_id="peer-3",
        )

    def grant(self, email, *codenames):
        user = User.objects.get(email=email)
        for codename in codenames:
            user.user_permissions.add(Permission.objects.get(codename=codename))
        return user

    def jobs(self):
        """
        Scoped on purpose: the async runner tests commit their rows on a separate
        connection, so the table is never pristine.
        """
        return FleetJob.objects.filter(tenant__in=(self.tenant, self.other_tenant))

    def create(self, token=None, **payload):
        payload.setdefault("action", "uptime")
        return self.client.post(
            reverse("fleet:job-list"),
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=token or self.bearer_token,
        )

    def test_catalog_lists_the_menu(self):
        response = self.get(reverse("fleet:action-catalog"), HTTP_AUTHORIZATION=self.bearer_token)
        self.assertEqual(response.status_code, 200)

        names = {row["name"] for row in response.data["results"]}
        self.assertEqual(names, set(ACTIONS))
        self.assertNotIn("template", response.data["results"][0], "the command itself never leaves the server")

    def test_running_a_job_needs_the_permission(self):
        response = self.create(token=self.karina_token, node_ids=[str(self.node.id)])
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.jobs().exists())

    def test_a_task_is_created_for_every_node_up_front(self):
        response = self.create(node_ids=[str(self.node.id), str(self.second_node.id)])

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], FleetJob.STATUS.PENDING)
        self.assertEqual(response.data["counts"]["total"], 2)
        self.assertEqual(response.data["counts"]["pending"], 2)
        self.assertEqual(
            {task["node_code"] for task in response.data["tasks"]},
            {self.node.code, self.second_node.code},
        )

        job = FleetJob.objects.get(pk=response.data["id"])
        self.assertEqual(job.tenant_id, self.tenant.id)
        self.assertEqual(job.tasks.count(), 2)

    def test_the_runner_is_dispatched_once_the_job_is_committed(self):
        with patch("fleet.tasks.run_fleet_job.delay") as delay:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.create(node_ids=[str(self.node.id)])

        self.assertEqual(response.status_code, 201)
        delay.assert_called_once_with(str(response.data["id"]))

    def test_the_job_is_audited(self):
        response = self.create(node_ids=[str(self.node.id)])

        log = FleetAuditLog.objects.filter(action=FleetAuditLog.ACTION.JOB_STARTED).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.detail["job_id"], str(response.data["id"]))
        self.assertEqual(log.detail["nodes"], [self.node.code])

    def test_an_unknown_node_id_is_named_and_nothing_is_created(self):
        missing = "11111111-1111-1111-1111-111111111111"
        response = self.create(node_ids=[str(self.node.id), missing])

        self.assertEqual(response.status_code, 400)
        self.assertIn(missing, str(response.data["node_ids"]))
        self.assertFalse(self.jobs().exists(), "a rejected target must not leave a half-built job")

    def test_a_foreign_node_is_only_ever_reported_as_missing(self):
        self.grant("angelina@gmail.com", "run_fleetjob", "view_fleetjob")
        response = self.create(token=self.angelina_token, node_ids=[str(self.node.id)])

        self.assertEqual(response.status_code, 400)
        self.assertIn(str(self.node.id), str(response.data["node_ids"]))
        self.assertNotIn("tenant", response.data)

    def test_a_selection_spanning_two_tenants_is_refused(self):
        response = self.create(node_ids=[str(self.node.id), str(self.foreign_node.id)])

        self.assertEqual(response.status_code, 400)
        self.assertIn("same tenant", str(response.data["node_ids"]))

    def test_all_nodes_needs_a_tenant_from_a_superuser(self):
        response = self.create(all_nodes=True)

        self.assertEqual(response.status_code, 400)
        self.assertIn("tenant", response.data)

    def test_all_nodes_uses_the_named_tenant(self):
        response = self.create(all_nodes=True, tenant=str(self.tenant.id))

        self.assertEqual(response.status_code, 201)
        codes = {task["node_code"] for task in response.data["tasks"]}
        self.assertEqual(codes, {self.node.code, self.second_node.code})

    def test_all_nodes_for_a_tenant_user_needs_no_tenant(self):
        self.grant("angelina@gmail.com", "run_fleetjob", "view_fleetjob")
        response = self.create(token=self.angelina_token, all_nodes=True)

        self.assertEqual(response.status_code, 201)
        self.assertIn(self.foreign_node.code, {task["node_code"] for task in response.data["tasks"]})
        self.assertNotIn(self.node.code, {task["node_code"] for task in response.data["tasks"]})

    def test_targets_must_be_given_one_way_or_the_other(self):
        self.assertEqual(self.create().status_code, 400)
        self.assertEqual(self.create(all_nodes=True, node_ids=[str(self.node.id)]).status_code, 400)

    def test_bad_params_are_caught_before_a_job_exists(self):
        response = self.create(action="uptime", params={"lines": "; reboot"}, node_ids=[str(self.node.id)])

        self.assertEqual(response.status_code, 400)
        self.assertIn("params", response.data)
        self.assertFalse(self.jobs().exists())

    def test_an_unknown_action_is_a_400(self):
        response = self.create(action="rm_rf_slash", node_ids=[str(self.node.id)])
        self.assertEqual(response.status_code, 400)

    @override_settings(FLEET_JOB_MAX_NODES=1)
    def test_the_node_cap_is_enforced(self):
        response = self.create(node_ids=[str(self.node.id), str(self.second_node.id)])

        self.assertEqual(response.status_code, 400)
        self.assertIn("at most 1", str(response.data["node_ids"]))

    def test_cancel_marks_everything_not_yet_started(self):
        job_id = self.create(node_ids=[str(self.node.id), str(self.second_node.id)]).data["id"]

        response = self.client.post(
            reverse("fleet:job-cancel", args=[job_id]),
            HTTP_AUTHORIZATION=self.bearer_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], FleetJob.STATUS.CANCELLED)
        self.assertEqual(response.data["counts"]["cancelled"], 2)
        self.assertTrue(
            all(task.finished_at for task in FleetJobTask.objects.filter(job_id=job_id)),
        )
        self.assertTrue(FleetAuditLog.objects.filter(action=FleetAuditLog.ACTION.JOB_CANCELLED).exists())

    def test_cancelling_a_finished_job_is_a_400(self):
        job_id = self.create(node_ids=[str(self.node.id)]).data["id"]
        FleetJob.objects.filter(pk=job_id).update(status=FleetJob.STATUS.DONE)

        response = self.client.post(
            reverse("fleet:job-cancel", args=[job_id]),
            HTTP_AUTHORIZATION=self.bearer_token,
        )
        self.assertEqual(response.status_code, 400)

    def test_a_job_from_another_tenant_is_not_found(self):
        job_id = self.create(node_ids=[str(self.node.id)]).data["id"]
        self.grant("angelina@gmail.com", "view_fleetjob")

        response = self.get(reverse("fleet:job-detail", args=[job_id]), HTTP_AUTHORIZATION=self.angelina_token)
        self.assertEqual(response.status_code, 404)

    def test_the_list_is_scoped_and_filterable(self):
        self.create(node_ids=[str(self.node.id)])
        # Straight to the table: an action that has since left the catalog cannot
        # be created through the API, and its rows must stay listable.
        FleetJob.objects.create(tenant=self.tenant, action="withdrawn_action")

        response = self.get(
            f"{reverse('fleet:job-list')}?action=uptime",
            HTTP_AUTHORIZATION=self.bearer_token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual({row["action"] for row in response.data["results"]}, {"uptime"})
        self.assertEqual(response.data["results"][0]["counts"]["total"], 1)


class RunFleetJobTest(BaseTestCase):
    """
    The Celery entrypoint around the fan-out: status transitions and redelivery.

    The fan-out is stubbed here and exercised for real in ``test_job_runner`` —
    it runs on its own thread with its own connection, which cannot see rows a
    wrapped test has not committed.
    """

    def setUp(self):
        self.tenant = create_tenant()
        self.node = create_node(tenant=self.tenant)

    def make_job(self, action="uptime", status=FleetJob.STATUS.PENDING):
        job = FleetJob.objects.create(tenant=self.tenant, action=action, status=status)
        FleetJobTask.objects.create(job=job, node=self.node, node_code=self.node.code)
        return job

    def test_the_job_is_started_and_closed_around_the_fan_out(self):
        job = self.make_job()

        with patch("fleet.tasks._fan_out", new=AsyncMock()) as fan_out:
            run_fleet_job(str(job.id))

        command, timeout = fan_out.await_args.args[1], fan_out.await_args.args[2]
        self.assertEqual(command, "uptime")
        self.assertEqual(timeout, ACTIONS["uptime"].timeout)

        job.refresh_from_db()
        self.assertEqual(job.status, FleetJob.STATUS.DONE)
        self.assertTrue(job.started_at and job.finished_at)

    def test_a_node_the_fan_out_never_reached_is_written_off(self):
        job = self.make_job()

        with patch("fleet.tasks._fan_out", new=AsyncMock()):
            run_fleet_job(str(job.id))

        task = job.tasks.get()
        self.assertEqual(task.status, FleetJobTask.STATUS.FAILED)
        self.assertIn("before this node was reached", task.error)

    def test_a_redelivered_job_is_not_run_twice(self):
        job = self.make_job(status=FleetJob.STATUS.RUNNING)

        with patch("fleet.tasks._fan_out", new=AsyncMock()) as fan_out:
            run_fleet_job(str(job.id))

        fan_out.assert_not_awaited()
        job.refresh_from_db()
        self.assertEqual(job.status, FleetJob.STATUS.RUNNING)

    def test_a_job_cancelled_before_it_started_touches_nothing(self):
        job = self.make_job(status=FleetJob.STATUS.CANCELLED)

        with patch("fleet.tasks._fan_out", new=AsyncMock()) as fan_out:
            run_fleet_job(str(job.id))

        fan_out.assert_not_awaited()
        self.assertEqual(job.tasks.get().status, FleetJobTask.STATUS.PENDING)

    def test_an_action_that_left_the_catalog_fails_the_job_cleanly(self):
        job = self.make_job()
        FleetJob.objects.filter(pk=job.id).update(action="withdrawn_action")

        with patch("fleet.tasks._fan_out", new=AsyncMock()) as fan_out:
            run_fleet_job(str(job.id))

        fan_out.assert_not_awaited()
        job.refresh_from_db()
        self.assertEqual(job.status, FleetJob.STATUS.DONE)
        self.assertEqual(job.tasks.get().status, FleetJobTask.STATUS.FAILED)

    def test_a_missing_job_is_a_no_op(self):
        run_fleet_job("11111111-1111-1111-1111-111111111111")

from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse

from core.tests.base import BaseTestCase
from fleet.models import FleetAuditLog, FleetNode
from fleet.netbird.exceptions import NetBirdUnavailable
from fleet.tests.factories import create_gateway
from main.models import Tenant
from users.models import User

TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"
OTHER_TENANT_ID = "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc"

INSTALL_SETTINGS = {
    "FLEET_INSTALL_BASE_URL": "https://grms.example.com",
    "FLEET_INSTALL_TOKEN_TTL_HOURS": 24,
    "NETBIRD_SETUP_KEY_TTL": 3600,
    "NETBIRD_HOTEL_GROUP_ID": "hotel-vms",
    "NETBIRD_MANAGEMENT_URL": "https://webrtc.example.com:443",
    "FLEET_SSH_PUBLIC_KEY": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITEST fleet@roomio",
}


class FleetNodeApiTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.tenant = Tenant.objects.get(pk=TENANT_ID)
        self.other_tenant = Tenant.objects.get(pk=OTHER_TENANT_ID)

        self.gateway = create_gateway(self.tenant, name="Front Desk")
        self.spare_gateway = create_gateway(self.tenant, name="Spa")
        self.foreign_gateway = create_gateway(self.other_tenant, name="Lobby")

        self.node = FleetNode.objects.create(
            tenant=self.tenant, gateway=self.gateway, code="tenant_1", mesh_ip="100.84.90.52"
        )
        self.foreign_node = FleetNode.objects.create(
            tenant=self.other_tenant, gateway=self.foreign_gateway, code="other_1"
        )

    def test_list_requires_authentication(self):
        response = self.get(reverse("fleet:node-list"))
        self.assertEqual(response.status_code, 401)

    def grant(self, email, codename):
        user = User.objects.get(email=email)
        user.user_permissions.add(Permission.objects.get(codename=codename))
        return user

    def codes_visible_to(self, token):
        """
        The async SSH/terminal tests commit their fixtures on a separate
        connection, so the table is not pristine — assert on containment.
        """
        response = self.get(f"{reverse('fleet:node-list')}?size=500", HTTP_AUTHORIZATION=token)
        self.assertEqual(response.status_code, 200)
        return {row["code"] for row in response.data["results"]}

    def test_superuser_sees_the_whole_fleet(self):
        codes = self.codes_visible_to(self.bearer_token)
        self.assertIn("tenant_1", codes)
        self.assertIn("other_1", codes, "a superuser is not scoped to one tenant")

    def test_list_is_scoped_to_the_users_tenant(self):
        self.grant("angelina@gmail.com", "view_fleetnode")
        codes = self.codes_visible_to(self.angelina_token)
        self.assertIn("other_1", codes)
        self.assertNotIn("tenant_1", codes)

    def test_user_without_permission_is_denied(self):
        response = self.get(reverse("fleet:node-list"), HTTP_AUTHORIZATION=self.karina_token)
        self.assertEqual(response.status_code, 403)

    def test_detail_of_a_foreign_node_is_not_found(self):
        response = self.get(
            reverse("fleet:node-detail", args=[self.foreign_node.id]),
            HTTP_AUTHORIZATION=self.angelina_token,
        )
        self.assertIn(response.status_code, (403, 404))

    def create(self, token=None, **payload):
        return self.client.post(
            reverse("fleet:node-list"),
            data=payload,
            HTTP_AUTHORIZATION=token or self.bearer_token,
        )

    def test_create_derives_the_code_from_the_tenant_and_gateway(self):
        response = self.create(gateway=str(self.spare_gateway.id), title="Spa VM")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["code"], "tenant_spa")
        self.assertEqual(str(response.data["tenant"]), TENANT_ID, "the gateway decides the tenant")
        self.assertEqual(response.data["gateway_name"], "Spa")
        self.assertEqual(response.data["ssh_user"], "roomio-agent")

    def test_create_requires_a_gateway(self):
        response = self.create(title="No gateway")
        self.assertEqual(response.status_code, 400)
        self.assertIn("gateway", response.data)

    def test_a_gateway_can_only_have_one_active_node(self):
        response = self.create(gateway=str(self.gateway.id))
        self.assertEqual(response.status_code, 400)
        self.assertIn("gateway", response.data)

    def test_a_plain_device_is_not_a_gateway(self):
        device = create_gateway(self.tenant, name="Thermostat", additional_info={})

        response = self.create(gateway=str(device.id))
        self.assertEqual(response.status_code, 400)
        self.assertIn("gateway", response.data)

    def test_a_superuser_with_no_tenant_still_creates_fine(self):
        """The gateway carries the tenant, so a tenant-less superuser is no longer stuck."""
        User.objects.filter(email="admin@gmail.com").update(tenant=None)

        response = self.create(gateway=str(self.spare_gateway.id))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(str(response.data["tenant"]), TENANT_ID)

    def test_tenant_user_cannot_create_on_a_foreign_gateway(self):
        self.grant("angelina@gmail.com", "add_fleetnode")

        response = self.create(token=self.angelina_token, gateway=str(self.spare_gateway.id))
        self.assertEqual(response.status_code, 400)
        self.assertIn("gateway", response.data)

    def test_soft_delete_hides_the_node_and_frees_the_gateway(self):
        with patch("fleet.views.fleet_node.release_peer") as release:
            response = self.client.delete(
                reverse("fleet:node-detail", args=[self.node.id]),
                HTTP_AUTHORIZATION=self.bearer_token,
            )

        self.assertEqual(response.status_code, 204)
        release.assert_called_once()

        self.node.refresh_from_db()
        self.assertFalse(self.node.is_active)

        # The gateway is free again, and the freed code is reusable.
        self.assertEqual(self.create(gateway=str(self.gateway.id)).status_code, 201)

    def test_delete_leaves_the_node_alone_if_the_peer_cannot_be_released(self):
        """A live peer for a gateway that is about to be re-claimed is the bug to avoid."""
        with patch("fleet.views.fleet_node.release_peer", side_effect=NetBirdUnavailable("down")):
            response = self.client.delete(
                reverse("fleet:node-detail", args=[self.node.id]),
                HTTP_AUTHORIZATION=self.bearer_token,
            )

        self.assertEqual(response.status_code, 400)
        self.node.refresh_from_db()
        self.assertTrue(self.node.is_active)

    def install(self, node=None):
        client = MagicMock(
            create_setup_key=MagicMock(return_value={"id": "key-1", "key": "SETUPKEY123"}),
            delete_peer=MagicMock(),
            delete_setup_key=MagicMock(),
        )
        with patch("fleet.enroll.NetBirdClient", return_value=client):
            response = self.client.post(
                reverse("fleet:node-install", args=[(node or self.node).id]),
                HTTP_AUTHORIZATION=self.bearer_token,
            )
        return response, client

    @override_settings(**INSTALL_SETTINGS)
    def test_install_returns_the_link_and_the_one_liner(self):
        response, _ = self.install()
        self.assertEqual(response.status_code, 200)

        self.node.refresh_from_db()
        self.assertIn(self.node.install_token, response.data["command"])
        self.assertTrue(response.data["command"].startswith("curl -fsSL"))
        self.assertIn("| sudo bash", response.data["command"])
        self.assertIn("/install/tenant_1", response.data["install_url"])

        self.assertEqual(response.data["hostname"], "tenant_1")
        self.assertFalse(response.data["peer_replaced"])

    @override_settings(**INSTALL_SETTINGS)
    def test_install_on_an_enrolled_node_replaces_the_peer(self):
        FleetNode.objects.filter(pk=self.node.pk).update(netbird_peer_id="peer-old", netbird_setup_key_id="key-old")

        response, client = self.install()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["peer_replaced"])
        client.delete_peer.assert_called_once_with("peer-old")
        client.delete_setup_key.assert_called_once_with("key-old")
        self.assertEqual(response.data["hostname"], "tenant_1", "the peer name must not change")

    @override_settings(**INSTALL_SETTINGS)
    def test_install_reports_a_netbird_outage(self):
        with patch("fleet.enroll.NetBirdClient", side_effect=NetBirdUnavailable("down")):
            response = self.client.post(
                reverse("fleet:node-install", args=[self.node.id]),
                HTTP_AUTHORIZATION=self.bearer_token,
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("netbird", response.data)

    def test_run_command_reports_output_and_is_audited(self):
        result = {"rc": 0, "stdout": "up 3 days\n", "stderr": ""}
        with patch("fleet.views.fleet_node.ssh.run_command_sync", return_value=result) as runner:
            response = self.client.post(
                reverse("fleet:node-run", args=[self.node.id]),
                data={"command": "uptime"},
                HTTP_AUTHORIZATION=self.bearer_token,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["stdout"], "up 3 days\n")
        runner.assert_called_once()

        log = FleetAuditLog.objects.filter(node=self.node, action=FleetAuditLog.ACTION.COMMAND_RUN).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.detail["command"], "uptime")

    def test_run_command_is_denied_without_permission(self):
        response = self.client.post(
            reverse("fleet:node-run", args=[self.node.id]),
            data={"command": "uptime"},
            HTTP_AUTHORIZATION=self.karina_token,
        )
        self.assertEqual(response.status_code, 403)

    def test_audit_log_endpoint_lists_node_history(self):
        FleetAuditLog.objects.create(node=self.node, action=FleetAuditLog.ACTION.PEER_PINNED, detail={})

        response = self.get(
            reverse("fleet:node-audit-logs", args=[self.node.id]),
            HTTP_AUTHORIZATION=self.bearer_token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["action"], FleetAuditLog.ACTION.PEER_PINNED)

    @patch("fleet.tasks.notify")
    @patch("fleet.tasks.NetBirdClient")
    def test_refresh_forces_a_poll(self, client_cls, _notify):
        peer = {
            "id": "peer-9",
            "name": "tenant_1",
            "hostname": "grms-roomio",
            "ip": "100.84.90.52",
            "connected": True,
            "last_seen": None,
            "groups": [],
        }
        client_cls.return_value = MagicMock(list_peers=MagicMock(return_value=[peer]))

        response = self.client.post(
            reverse("fleet:node-refresh", args=[self.node.id]),
            HTTP_AUTHORIZATION=self.bearer_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_online"])

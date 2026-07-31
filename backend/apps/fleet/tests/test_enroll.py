from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from core.utils.get_time import get_mil_sec
from fleet.enroll import (
    EnrollmentError,
    issue_install_token,
    prepare_enrollment,
    release_peer,
    render_bootstrap,
    verify_install_token,
)
from fleet.models import FleetAuditLog, FleetNode
from fleet.netbird.exceptions import NetBirdAPIError, NetBirdUnavailable
from fleet.tests.factories import create_gateway
from main.models import Tenant

TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"

ENROLL_SETTINGS = {
    "FLEET_SSH_PUBLIC_KEY": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITEST fleet@roomio",
    "NETBIRD_MANAGEMENT_URL": "https://webrtc.example.com:443",
    "NETBIRD_HOTEL_GROUP_ID": "hotel-vms",
    "NETBIRD_SETUP_KEY_TTL": 3600,
    "FLEET_INSTALL_TOKEN_TTL_HOURS": 24,
    "FLEET_INSTALL_BASE_URL": "https://grms.example.com",
}


def fake_client(key="SETUPKEY123", key_id="key-1"):
    return MagicMock(
        create_setup_key=MagicMock(return_value={"id": key_id, "key": key}),
        delete_peer=MagicMock(),
        delete_setup_key=MagicMock(),
    )


class NodeTestCase(TestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml")

    def setUp(self):
        gateway = create_gateway(Tenant.objects.get(pk=TENANT_ID), name="Front Desk")
        self.node = FleetNode.objects.create(tenant_id=TENANT_ID, gateway=gateway, code="tenant_1")


@override_settings(**ENROLL_SETTINGS)
class TokenLifecycleTest(NodeTestCase):
    def test_issuing_a_token_records_an_audit_entry(self):
        issue_install_token(self.node)
        self.assertTrue(self.node.install_token)
        self.assertGreater(self.node.token_expires_at, get_mil_sec())
        self.assertTrue(FleetAuditLog.objects.filter(node=self.node, action=FleetAuditLog.ACTION.TOKEN_ISSUED).exists())

    def test_link_never_outlives_the_setup_key(self):
        """A 24h link handing out a 1h key would be a link that mostly 410s."""
        issue_install_token(self.node)
        self.assertLessEqual(self.node.token_expires_at - get_mil_sec(), 3600 * 1000)

    def test_reissuing_invalidates_the_previous_link(self):
        self.node.netbird_setup_key = "K"
        issue_install_token(self.node)
        first = self.node.install_token

        issue_install_token(self.node)
        self.assertNotEqual(first, self.node.install_token)
        with self.assertRaises(EnrollmentError):
            verify_install_token(self.node, first)

    def test_verify_rejects_wrong_expired_used_and_keyless_tokens(self):
        self.node.netbird_setup_key = "K"
        issue_install_token(self.node)
        verify_install_token(self.node, self.node.install_token)  # the happy path

        with self.assertRaises(EnrollmentError):
            verify_install_token(self.node, "not-the-token")

        self.node.token_used_at = get_mil_sec()
        with self.assertRaises(EnrollmentError):
            verify_install_token(self.node, self.node.install_token)

        self.node.token_used_at = None
        self.node.token_expires_at = get_mil_sec() - 1000
        with self.assertRaises(EnrollmentError):
            verify_install_token(self.node, self.node.install_token)

        self.node.token_expires_at = get_mil_sec() + 1000
        self.node.netbird_setup_key = None
        with self.assertRaises(EnrollmentError):
            verify_install_token(self.node, self.node.install_token)


@override_settings(**ENROLL_SETTINGS)
class PeerLifecycleTest(NodeTestCase):
    """One active peer per gateway: whatever came before is torn down first."""

    def prepare(self, client=None):
        client = client or fake_client()
        with patch("fleet.enroll.NetBirdClient", return_value=client):
            key = prepare_enrollment(self.node)
        return client, key

    def test_first_enrollment_mints_a_key_and_deletes_nothing(self):
        client, key = self.prepare()

        self.assertEqual(key, "SETUPKEY123")
        client.delete_peer.assert_not_called()
        client.delete_setup_key.assert_not_called()

        self.node.refresh_from_db()
        self.assertEqual(self.node.netbird_setup_key_id, "key-1")
        self.assertEqual(self.node.netbird_setup_key, "SETUPKEY123")
        self.assertTrue(self.node.install_token)

    def test_setup_key_is_single_use_and_lands_in_the_hotel_group(self):
        client, _ = self.prepare()

        kwargs = client.create_setup_key.call_args.kwargs
        self.assertEqual(kwargs["usage_limit"], 1)
        self.assertEqual(kwargs["auto_groups"], ["hotel-vms"])
        self.assertEqual(kwargs["name"], "node-tenant_1")

    def test_re_enrolling_deletes_the_old_peer_and_its_key(self):
        FleetNode.objects.filter(pk=self.node.pk).update(
            netbird_peer_id="peer-old",
            netbird_setup_key_id="key-old",
            mesh_ip="100.84.1.1",
            is_online=True,
            ssh_host_key="ssh-ed25519 AAAAOLD",
        )
        self.node.refresh_from_db()

        client, _ = self.prepare(fake_client(key="NEWKEY", key_id="key-2"))

        client.delete_peer.assert_called_once_with("peer-old")
        client.delete_setup_key.assert_called_once_with("key-old")

        self.node.refresh_from_db()
        self.assertIsNone(self.node.netbird_peer_id, "the pin must be cleared or the new peer reads as an impostor")
        self.assertIsNone(self.node.mesh_ip)
        self.assertIsNone(self.node.ssh_host_key)
        self.assertFalse(self.node.is_online)
        self.assertEqual(self.node.netbird_setup_key_id, "key-2")

    def test_re_enrolling_keeps_the_same_peer_name(self):
        FleetNode.objects.filter(pk=self.node.pk).update(netbird_peer_id="peer-old")
        self.node.refresh_from_db()

        _, key = self.prepare()
        self.assertIn("--hostname tenant_1", render_bootstrap(self.node, key))

    def test_re_enrolling_is_audited(self):
        FleetNode.objects.filter(pk=self.node.pk).update(netbird_peer_id="peer-old", netbird_setup_key_id="key-old")
        self.node.refresh_from_db()
        self.prepare()

        actions = set(FleetAuditLog.objects.filter(node=self.node).values_list("action", flat=True))
        self.assertEqual(
            {
                FleetAuditLog.ACTION.PEER_DELETED,
                FleetAuditLog.ACTION.SETUP_KEY_DELETED,
                FleetAuditLog.ACTION.SETUP_KEY_CREATED,
                FleetAuditLog.ACTION.TOKEN_ISSUED,
            },
            actions,
        )

    def test_a_peer_netbird_already_dropped_counts_as_released(self):
        FleetNode.objects.filter(pk=self.node.pk).update(netbird_peer_id="peer-gone")
        self.node.refresh_from_db()

        client = fake_client()
        client.delete_peer.side_effect = NetBirdAPIError(404, "not found")
        release_peer(self.node, client=client)

        self.node.refresh_from_db()
        self.assertIsNone(self.node.netbird_peer_id)

    def test_a_real_delete_failure_is_not_swallowed(self):
        FleetNode.objects.filter(pk=self.node.pk).update(netbird_peer_id="peer-1")
        self.node.refresh_from_db()

        client = fake_client()
        client.delete_peer.side_effect = NetBirdAPIError(500, "boom")
        with self.assertRaises(NetBirdAPIError):
            release_peer(self.node, client=client)

        self.node.refresh_from_db()
        self.assertEqual(self.node.netbird_peer_id, "peer-1", "a failed delete must not orphan the peer")


@override_settings(**ENROLL_SETTINGS)
class BootstrapScriptTest(NodeTestCase):
    def script(self):
        return render_bootstrap(self.node, "SETUPKEY123")

    def test_carries_the_key_hostname_and_public_key(self):
        script = self.script()
        self.assertIn("SETUPKEY123", script)
        self.assertIn("--allow-server-ssh=false", script)
        self.assertIn("--hostname tenant_1", script)
        self.assertIn(ENROLL_SETTINGS["FLEET_SSH_PUBLIC_KEY"], script)
        self.assertIn("netbird down", script)

    def test_netbird_up_stays_on_a_single_line(self):
        """A line continuation followed by a blank line silently breaks the join."""
        up_lines = [line for line in self.script().splitlines() if line.startswith("netbird up ")]
        self.assertEqual(len(up_lines), 1)
        self.assertFalse(up_lines[0].rstrip().endswith("\\"))

    def test_uses_no_shell_variables(self):
        """
        Every value is a literal: variables only exist inside one shell process,
        so a paste interrupted halfway silently loses them.
        """
        script = self.script()
        self.assertNotIn("${", script)
        self.assertNotIn("SSH_USER=", script)
        self.assertNotIn("SSH_HOME=", script)

    def test_runs_apt_non_interactively(self):
        """No TTY behind a pipe, so a needrestart prompt would hang forever."""
        script = self.script()
        self.assertIn("DEBIAN_FRONTEND=noninteractive", script)
        self.assertIn("NEEDRESTART_MODE=a", script)

    def test_never_calls_sudo_itself(self):
        """The whole script is already root — an inner sudo would prompt again."""
        self.assertEqual([ln for ln in self.script().splitlines() if ln.lstrip().startswith("sudo ")], [])

    def test_sudoers_is_validated_before_it_is_installed(self):
        """A malformed /etc/sudoers.d file locks sudo out for everyone."""
        script = self.script()
        self.assertLess(script.index("visudo -cf"), script.index("mv /etc/sudoers.d/"))


@override_settings(**ENROLL_SETTINGS)
class InstallEndpointTest(NodeTestCase):
    """The public `curl … | sudo bash` URL. The key is already minted by now."""

    def setUp(self):
        super().setUp()
        with patch("fleet.enroll.NetBirdClient", return_value=fake_client()):
            prepare_enrollment(self.node)

    def url(self, token=None, code=None):
        return f"/install/{code or self.node.code}?t={token if token is not None else self.node.install_token}"

    def test_serves_the_script_with_the_key_injected(self):
        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 200)
        self.assertIn("SETUPKEY123", response.content.decode())
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_token_is_single_use_and_the_key_is_wiped(self):
        self.assertEqual(self.client.get(self.url()).status_code, 200)
        self.assertEqual(self.client.get(self.url()).status_code, 410)

        self.node.refresh_from_db()
        self.assertIsNone(self.node.netbird_setup_key, "the plaintext key must not outlive the fetch")
        self.assertEqual(self.node.netbird_setup_key_id, "key-1", "but the id must survive, to delete the key later")

    def test_bad_token_and_unknown_node_look_identical(self):
        wrong = self.client.get(self.url(token="nope"))
        unknown = self.client.get(self.url(code="does_not_exist"))

        self.assertEqual(wrong.status_code, 410)
        self.assertEqual(unknown.status_code, 410)
        self.assertEqual(wrong.content, unknown.content)

    def test_expired_token_is_rejected(self):
        FleetNode.objects.filter(pk=self.node.pk).update(token_expires_at=get_mil_sec() - 1)
        self.assertEqual(self.client.get(self.url()).status_code, 410)

    @override_settings(FLEET_SSH_PUBLIC_KEY="")
    def test_refuses_to_serve_without_a_public_key(self):
        """An empty authorized_keys would enroll a node we could never log into."""
        self.assertEqual(self.client.get(self.url()).status_code, 503)

    def test_serving_is_audited(self):
        self.client.get(self.url())
        self.assertTrue(
            FleetAuditLog.objects.filter(node=self.node, action=FleetAuditLog.ACTION.BOOTSTRAP_SERVED).exists()
        )

    def test_a_netbird_outage_cannot_break_the_link(self):
        """Nothing here talks to NetBird any more — the key was minted earlier."""
        with patch("fleet.enroll.NetBirdClient", side_effect=NetBirdUnavailable("down")):
            self.assertEqual(self.client.get(self.url()).status_code, 200)

from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from core.utils.get_time import get_mil_sec
from fleet.models import FleetAuditLog, FleetNode
from fleet.netbird.exceptions import NetBirdUnavailable
from fleet.tasks import apply_peer, peer_name, poll_fleet_peers, sweep_unconfirmed
from fleet.tests.factories import create_gateway
from fleet.utils.time import to_mil_sec
from main.models import Tenant

TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"


def now_rfc3339():
    return timezone.now().isoformat().replace("+00:00", "Z")


def make_peer(**overrides):
    peer = {
        "id": "peer-1",
        "name": "tenant_1",
        "hostname": "grms-roomio",
        "ip": "100.84.90.52",
        "connected": True,
        "last_seen": now_rfc3339(),
        "os": "Ubuntu 24.04",
        "version": "0.74.7",
        "groups": [{"id": "hotel-vms"}],
    }
    peer.update(overrides)
    return peer


class PollerTest(TestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml")

    def setUp(self):
        gateway = create_gateway(Tenant.objects.get(pk=TENANT_ID), name="Front Desk")
        self.node = FleetNode.objects.create(tenant_id=TENANT_ID, gateway=gateway, code="tenant_1")

    def test_peer_is_matched_on_name_and_nothing_else(self):
        """
        `hostname` is the VM's own OS hostname and `dns_label` is the DNS-safe
        form — matching on either silently leaves every node offline.
        """
        self.assertEqual(peer_name({"name": "tenant_1", "hostname": "grms-roomio"}), "tenant_1")
        self.assertEqual(peer_name({"hostname": "grms-roomio"}), "")
        self.assertEqual(peer_name({"dns_label": "tenant-1.netbird.selfhosted"}), "")
        self.assertEqual(peer_name({}), "")

    @patch("fleet.observables.fleet_node._send")
    @patch("fleet.tasks.NetBirdClient")
    def test_poll_matches_a_real_netbird_payload(self, client_cls, _send):
        """The shape NetBird 0.75 actually returns: name is ours, hostname is the VM's."""
        peer = make_peer(name="tenant_1", hostname="grms-roomio", dns_label="tenant-1.netbird.selfhosted")
        client_cls.return_value = MagicMock(list_peers=MagicMock(return_value=[peer]))

        poll_fleet_peers()

        self.node.refresh_from_db()
        self.assertTrue(self.node.is_online)
        self.assertEqual(self.node.mesh_ip, "100.84.90.52")

    def test_first_sight_pins_the_peer_and_registers_the_node(self):
        self.assertTrue(apply_peer(self.node, make_peer()))
        self.node.refresh_from_db()

        self.assertEqual(self.node.netbird_peer_id, "peer-1")
        self.assertEqual(self.node.mesh_ip, "100.84.90.52")
        self.assertTrue(self.node.is_online)
        self.assertEqual(self.node.os, "Ubuntu 24.04")
        self.assertIsNotNone(self.node.enrolled_at)
        self.assertTrue(FleetAuditLog.objects.filter(node=self.node, action=FleetAuditLog.ACTION.PEER_PINNED).exists())

    def test_unchanged_peer_is_not_rewritten(self):
        peer = make_peer()
        apply_peer(self.node, peer)
        self.assertFalse(apply_peer(self.node, peer))

    def test_peer_id_mismatch_is_refused(self):
        apply_peer(self.node, make_peer())

        impostor = make_peer(id="peer-666", ip="100.84.99.99")
        self.assertFalse(apply_peer(self.node, impostor))

        self.node.refresh_from_db()
        self.assertEqual(self.node.netbird_peer_id, "peer-1")
        self.assertEqual(self.node.mesh_ip, "100.84.90.52", "a copied hostname must never repoint the mesh IP")
        self.assertTrue(
            FleetAuditLog.objects.filter(node=self.node, action=FleetAuditLog.ACTION.PEER_MISMATCH).exists()
        )

    def test_disconnected_peer_goes_offline(self):
        apply_peer(self.node, make_peer())
        apply_peer(self.node, make_peer(connected=False))
        self.node.refresh_from_db()
        self.assertFalse(self.node.is_online)

    def test_sweep_marks_unconfirmed_nodes_offline(self):
        FleetNode.objects.filter(pk=self.node.pk).update(is_online=True)
        self.assertIn(self.node.id, sweep_unconfirmed([]))
        self.node.refresh_from_db()
        self.assertFalse(self.node.is_online)

    def test_confirmed_node_survives_a_stale_last_seen(self):
        """NetBird does not always refresh last_seen while a peer stays connected."""
        old = get_mil_sec() - 3600 * 1000
        FleetNode.objects.filter(pk=self.node.pk).update(is_online=True, last_seen=old)

        self.assertEqual(sweep_unconfirmed([self.node.id]), [])
        self.node.refresh_from_db()
        self.assertTrue(self.node.is_online)

    @patch("fleet.observables.fleet_node._send")
    @patch("fleet.tasks.NetBirdClient")
    def test_netbird_outage_leaves_status_untouched(self, client_cls, _send):
        client_cls.return_value = MagicMock(list_peers=MagicMock(side_effect=NetBirdUnavailable("down")))
        old = get_mil_sec() - 3600 * 1000
        FleetNode.objects.filter(pk=self.node.pk).update(is_online=True, last_seen=old)

        poll_fleet_peers()

        self.node.refresh_from_db()
        self.assertTrue(self.node.is_online)

    def test_last_seen_is_stored_in_milliseconds(self):
        peer = make_peer()
        apply_peer(self.node, peer)
        self.node.refresh_from_db()
        self.assertEqual(self.node.last_seen, to_mil_sec(peer["last_seen"]))

    @patch("fleet.observables.fleet_node._send")
    @patch("fleet.tasks.NetBirdClient")
    def test_poll_reconciles_against_netbird(self, client_cls, _send):
        client_cls.return_value = MagicMock(list_peers=MagicMock(return_value=[make_peer()]))

        poll_fleet_peers()

        self.node.refresh_from_db()
        self.assertTrue(self.node.is_online)
        self.assertEqual(self.node.netbird_peer_id, "peer-1")

    @patch("fleet.observables.fleet_node._send")
    @patch("fleet.tasks.NetBirdClient")
    def test_poll_ignores_peers_with_no_matching_node(self, client_cls, _send):
        client_cls.return_value = MagicMock(list_peers=MagicMock(return_value=[make_peer(name="someone_else")]))

        poll_fleet_peers()

        self.node.refresh_from_db()
        self.assertIsNone(self.node.netbird_peer_id)
        self.assertFalse(self.node.is_online)

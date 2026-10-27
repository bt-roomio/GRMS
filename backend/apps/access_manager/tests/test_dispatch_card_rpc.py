from unittest.mock import call, patch

from django.test import TestCase

from access_manager.models import Card, GuestCard
from access_manager.tests.test_password_credential import FIXTURES
from access_manager.utilits.dispatch_card_rpc import dispatch_card_rpc
from access_manager.utilits.get_device_cards import get_device_cards
from main.models import Device, Guest, Room


class DispatchCardRpcTest(TestCase):
    fixtures = FIXTURES

    def setUp(self):
        self.device_id = "47aef21b-6cc9-4ec5-8573-1a6f491940c0"
        self.guest_id = "5b66af57-fb27-4c26-9986-b9994e644605"
        self.device = Device.objects.get(id=self.device_id)
        self.tenant_id = self.device.tenant_id
        Card.objects.create(number="482915", tenant_id=self.tenant_id, is_pwd=True)
        Card.objects.create(number="739264", tenant_id=self.tenant_id, is_pwd=True)

    @patch("access_manager.utilits.dispatch_card_rpc.send_rpc_request", return_value={"success": True})
    def test_splits_rfid_and_pins(self, mock_send):
        dispatch_card_rpc(self.device_id, ["65 28 23 12", "482915", "739264"], 0, guest_id=self.guest_id)

        self.assertEqual(
            mock_send.call_args_list,
            [
                call(self.device_id, ["65 28 23 12"], 0, guest_id=self.guest_id),
                call(self.device_id, ["482915"], 0, is_pwd=True, guest_id=self.guest_id),
                call(self.device_id, ["739264"], 0, is_pwd=True, guest_id=self.guest_id),
            ],
        )

    @patch("access_manager.utilits.dispatch_card_rpc.send_rpc_request", return_value={"success": True})
    def test_pins_only_skips_rfid_request(self, mock_send):
        dispatch_card_rpc(self.device_id, ["482915"], 0)

        mock_send.assert_called_once_with(self.device_id, ["482915"], 0, is_pwd=True)

    @patch("access_manager.utilits.dispatch_card_rpc.send_rpc_request", return_value={"success": True})
    def test_rfid_only_returns_single_result(self, mock_send):
        result = dispatch_card_rpc(self.device_id, ["65 28 23 12"], 0)

        mock_send.assert_called_once_with(self.device_id, ["65 28 23 12"], 0)
        self.assertEqual(result, {"success": True})

    @patch("access_manager.utilits.dispatch_card_rpc.send_rpc_request")
    def test_merged_result_fails_when_any_request_fails(self, mock_send):
        mock_send.side_effect = [
            {"success": True, "message": "Cards are deactivated."},
            {"success": False, "message": "Time out error!"},
        ]

        result = dispatch_card_rpc(self.device_id, ["65 28 23 12", "482915"], 0)

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Time out error!")
        self.assertEqual(len(result["results"]), 2)

    def test_get_device_cards_excludes_pins(self):
        guest = Guest.objects.get(id=self.guest_id)
        pin = Card.objects.get(number="482915", tenant_id=self.tenant_id)
        GuestCard.objects.create(guest=guest, card=pin, is_active=True)
        self.device.room = guest.room
        self.device.save(update_fields=["room"])

        self.assertNotIn("482915", get_device_cards(self.device.id, [], connect=True))


class GuestCheckoutRemovesPinsTest(TestCase):
    fixtures = FIXTURES

    def setUp(self):
        self.guest = Guest.objects.get(id="5b66af57-fb27-4c26-9986-b9994e644605")
        pin = Card.objects.create(number="482915", tenant_id=self.guest.tenant_id, is_pwd=True)
        GuestCard.objects.create(guest=self.guest, card=pin, is_active=True)

    @patch("access_manager.utilits.dispatch_card_rpc.send_rpc_request", return_value={"success": True})
    def test_room_checkout_sends_pin_with_is_pwd(self, mock_send):
        Room.objects.guest_checkout(self.guest.room_id)

        pin_calls = [c for c in mock_send.call_args_list if c.kwargs.get("is_pwd")]
        self.assertTrue(pin_calls)
        for c in pin_calls:
            self.assertEqual(c.args[1], ["482915"])
            self.assertEqual(c.args[2], 0)
        for c in mock_send.call_args_list:
            if not c.kwargs.get("is_pwd"):
                self.assertNotIn("482915", c.args[1])

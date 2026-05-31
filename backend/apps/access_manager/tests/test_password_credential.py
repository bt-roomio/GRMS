from unittest.mock import patch

from django.test import TestCase

from access_manager.models import Card, GuestCard, NeedSyncDevice
from access_manager.serializers.guest_card import GuestCardRequestSerializer
from access_manager.tasks.send_rpc import send_rpc_request
from access_manager.utilits.prepare_rpc_request import prepare_rpc_request
from main.models import Device, Guest

FIXTURES = (
    "tenant_profile.yaml",
    "tenant.yaml",
    "roles_permissions.yaml",
    "users.yaml",
    "room.yaml",
    "guest.yaml",
    "public_space.yaml",
    "customer.yaml",
    "device_profile.yaml",
    "device.yaml",
    "group.yaml",
    "group_public_space.yaml",
    "group_room.yaml",
    "staff.yaml",
    "card.yaml",
    "card_slot.yaml",
    "guest_public_space.yaml",
    "guest_card.yaml",
    "staff_card.yaml",
    "need_sync_device.yaml",
)


class CardIsPwdDefaultTest(TestCase):
    fixtures = FIXTURES

    def test_existing_cards_default_to_false(self):
        for card in Card.objects.all():
            self.assertFalse(card.is_pwd, f"Card {card.id} should default is_pwd=False")

    def test_new_card_with_is_pwd_true(self):
        tenant_id = Card.objects.first().tenant_id
        card = Card.objects.create(number="99 99 99 99", tenant_id=tenant_id, is_pwd=True)
        card.refresh_from_db()
        self.assertTrue(card.is_pwd)


class GuestCardRequestSerializerPwdTest(TestCase):
    def test_is_pwd_false_keeps_all_cards(self):
        s = GuestCardRequestSerializer(data={"guest_id": "g", "cards": ["111", "222", "333"]})
        s.is_valid(raise_exception=True)
        self.assertEqual(s.validated_data["cards"], ["111", "222", "333"])
        self.assertFalse(s.validated_data["is_pwd"])

    def test_is_pwd_true_truncates_to_first(self):
        s = GuestCardRequestSerializer(data={"guest_id": "g", "cards": ["111", "222", "333"], "is_pwd": True})
        s.is_valid(raise_exception=True)
        self.assertEqual(s.validated_data["cards"], ["48291"])
        self.assertTrue(s.validated_data["is_pwd"])

    def test_is_pwd_true_with_single_card_unchanged(self):
        s = GuestCardRequestSerializer(data={"guest_id": "g", "cards": ["12345"], "is_pwd": True})
        s.is_valid(raise_exception=True)
        self.assertEqual(s.validated_data["cards"], ["48291"])

    def test_is_pwd_true_rejects_repeated_digits(self):
        s = GuestCardRequestSerializer(
            data={"guest_id": "g", "cards": ["1111"], "is_pwd": True}
        )
        self.assertFalse(s.is_valid())
        self.assertIn("cards", s.errors)

    def test_is_pwd_true_rejects_sequential_digits(self):
        s = GuestCardRequestSerializer(
            data={"guest_id": "g", "cards": ["1234"], "is_pwd": True}
        )
        self.assertFalse(s.is_valid())
        self.assertIn("cards", s.errors)

    def test_is_pwd_true_rejects_short_pin(self):
        s = GuestCardRequestSerializer(
            data={"guest_id": "g", "cards": ["12"], "is_pwd": True}
        )
        self.assertFalse(s.is_valid())
        self.assertIn("cards", s.errors)

    def test_is_pwd_true_rejects_non_numeric(self):
        s = GuestCardRequestSerializer(
            data={"guest_id": "g", "cards": ["12ab5"], "is_pwd": True}
        )
        self.assertFalse(s.is_valid())
        self.assertIn("cards", s.errors)


class PrepareRpcRequestPwdTest(TestCase):
    fixtures = FIXTURES

    def setUp(self):
        self.device_id = "47aef21b-6cc9-4ec5-8573-1a6f491940c0"
        self.guest_id = "5b66af57-fb27-4c26-9986-b9994e644605"
        self.guest_card_number = "65 28 23 12"

    def test_card_envelope_uses_writeRFID(self):
        result = prepare_rpc_request(
            device_id=self.device_id,
            cards=[self.guest_card_number],
            access=1,
            guest_id=self.guest_id,
        )
        rpc_data = result["message"]["data"]["data"]
        self.assertEqual(rpc_data["method"], "writeRFID")
        self.assertEqual(rpc_data["timeout"], 10000)
        self.assertIsInstance(rpc_data["params"], list)

    def test_pwd_envelope_uses_add_pwd_when_access_1(self):
        result = prepare_rpc_request(
            device_id=self.device_id,
            cards=["12345"],
            access=1,
            guest_id=self.guest_id,
            is_pwd=True,
        )
        rpc_data = result["message"]["data"]["data"]
        self.assertEqual(rpc_data["method"], "add_pwd")
        self.assertEqual(rpc_data["params"], {"password": 12345})
        self.assertEqual(rpc_data["timeout"], 10000)

    def test_pwd_envelope_uses_remove_pwd_when_access_0(self):
        result = prepare_rpc_request(
            device_id=self.device_id,
            cards=["67890"],
            access=0,
            guest_id=self.guest_id,
            is_pwd=True,
        )
        rpc_data = result["message"]["data"]["data"]
        self.assertEqual(rpc_data["method"], "delete_pwd")
        self.assertEqual(rpc_data["params"], {"password": 67890})

    def test_pwd_envelope_keeps_top_level_shape(self):
        result = prepare_rpc_request(
            device_id=self.device_id,
            cards=["42"],
            access=1,
            guest_id=self.guest_id,
            is_pwd=True,
        )
        msg = result["message"]
        self.assertEqual(msg["topic"], "v1/gateway/rpc")
        self.assertIn("targetDeviceUUID", msg)
        self.assertIn("device", msg["data"])
        self.assertIn("data", msg["data"])

    def test_card_envelope_unchanged_when_is_pwd_false(self):
        non_pwd = prepare_rpc_request(
            device_id=self.device_id,
            cards=[self.guest_card_number],
            access=1,
            guest_id=self.guest_id,
            is_pwd=False,
        )
        default = prepare_rpc_request(
            device_id=self.device_id,
            cards=[self.guest_card_number],
            access=1,
            guest_id=self.guest_id,
        )
        self.assertEqual(
            non_pwd["message"]["data"]["data"]["method"],
            default["message"]["data"]["data"]["method"],
        )
        self.assertEqual(non_pwd["message"]["data"]["data"]["method"], "writeRFID")


class SendRpcRequestPwdTest(TestCase):
    fixtures = FIXTURES

    def setUp(self):
        self.device_id = "47aef21b-6cc9-4ec5-8573-1a6f491940c0"
        self.guest_id = "5b66af57-fb27-4c26-9986-b9994e644605"
        self.guest = Guest.objects.get(id=self.guest_id)
        self.device = Device.objects.get(id=self.device_id)

    @patch("access_manager.tasks.send_rpc.connect_to_rabbitmq")
    @patch("access_manager.tasks.send_rpc.send_to_rabbitmq")
    def test_pwd_card_offline_creates_need_sync_with_pwd_flag(self, mock_send_rabbitmq, mock_connect_rabbitmq):
        card = Card.objects.create(number="55555", tenant_id=self.device.tenant_id, is_pwd=True)
        GuestCard.objects.create(guest=self.guest, card=card, is_active=True)
        self.device.status = False
        self.device.save()

        result = send_rpc_request(
            device_id=self.device_id,
            cards=["55555"],
            access=1,
            guest_id=self.guest_id,
            is_pwd=True,
        )

        self.assertFalse(result["success"])
        sync_row = NeedSyncDevice.objects.filter(card__number="55555", device=self.device).first()
        self.assertIsNotNone(sync_row)
        self.assertTrue(sync_row.card.is_pwd)


class SyncDevicesTaskPwdGroupingTest(TestCase):
    fixtures = FIXTURES

    def setUp(self):
        self.device_id = "47aef21b-6cc9-4ec5-8573-1a6f491940c0"
        self.device = Device.objects.get(id=self.device_id)
        self.tenant_id = self.device.tenant_id

    @patch("access_manager.tasks.sync_device.send_rpc_request")
    def test_pwd_rows_dispatch_with_is_pwd_true(self, mock_send_rpc):
        from access_manager.tasks.sync_device import sync_devices_task

        mock_send_rpc.return_value = {"success": True}
        pwd_card = Card.objects.create(number="77777", tenant_id=self.tenant_id, is_pwd=True)
        rfid_card = Card.objects.create(number="11 22 33 44", tenant_id=self.tenant_id, is_pwd=False)

        NeedSyncDevice.objects.create(
            card=pwd_card,
            device=self.device,
            need_sync=True,
            additional_info={"message_params": {"access": 1}},
        )
        NeedSyncDevice.objects.create(
            card=rfid_card,
            device=self.device,
            need_sync=True,
            additional_info={"message_params": {"access": 1}},
        )

        sync_devices_task(tenant_id=self.tenant_id)

        calls = mock_send_rpc.call_args_list
        pwd_calls = [c for c in calls if c.kwargs.get("is_pwd")]
        rfid_calls = [c for c in calls if not c.kwargs.get("is_pwd")]

        self.assertEqual(len(pwd_calls), 1)
        self.assertEqual(pwd_calls[0].args[1], ["77777"])
        self.assertEqual(len(rfid_calls), 1)
        self.assertIn("11 22 33 44", rfid_calls[0].args[1])

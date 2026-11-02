from unittest.mock import patch

from django.test import TestCase

from access_manager.models import Card, GuestCard, NeedSyncDevice
from access_manager.serializers.guest_card import GuestCardRequestSerializer
from access_manager.tasks.send_rpc import send_rpc_request
from access_manager.utilits.pin_to_card import pin_to_card_number
from access_manager.utilits.prepare_rpc_request import prepare_rpc_request
from main.models import Device, Guest
from users.models import User

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
        s = GuestCardRequestSerializer(data={"guest_id": "g", "cards": ["48291", "73826", "91527"], "is_pwd": True})
        s.is_valid(raise_exception=True)
        self.assertEqual(s.validated_data["cards"], ["48291"])
        self.assertTrue(s.validated_data["is_pwd"])

    def test_is_pwd_true_with_single_card_unchanged(self):
        s = GuestCardRequestSerializer(data={"guest_id": "g", "cards": ["48291"], "is_pwd": True})
        s.is_valid(raise_exception=True)
        self.assertEqual(s.validated_data["cards"], ["48291"])

    def test_is_pwd_true_rejects_repeated_digits(self):
        s = GuestCardRequestSerializer(data={"guest_id": "g", "cards": ["1111"], "is_pwd": True})
        self.assertFalse(s.is_valid())
        self.assertIn("cards", s.errors)

    def test_is_pwd_true_rejects_sequential_digits(self):
        s = GuestCardRequestSerializer(data={"guest_id": "g", "cards": ["1234"], "is_pwd": True})
        self.assertFalse(s.is_valid())
        self.assertIn("cards", s.errors)

    def test_is_pwd_true_rejects_short_pin(self):
        s = GuestCardRequestSerializer(data={"guest_id": "g", "cards": ["12"], "is_pwd": True})
        self.assertFalse(s.is_valid())
        self.assertIn("cards", s.errors)

    def test_is_pwd_true_rejects_non_numeric(self):
        s = GuestCardRequestSerializer(data={"guest_id": "g", "cards": ["12ab5"], "is_pwd": True})
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
        self.assertEqual(rpc_data["params"], {"password": "12345"})
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
        self.assertEqual(rpc_data["params"], {"password": "67890"})

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

    # A non-"default" device profile, so the Default-profile PIN guard does not short-circuit.
    NON_DEFAULT_PROFILE_ID = "be17d30b-9785-4415-bfa5-e7fdaf19e57c"  # name: "test_default"

    @patch("access_manager.tasks.send_rpc.connect_to_rabbitmq")
    @patch("access_manager.tasks.send_rpc.send_to_rabbitmq")
    def test_pwd_card_offline_creates_need_sync_with_pwd_flag(self, mock_send_rabbitmq, mock_connect_rabbitmq):
        card = Card.objects.create(number="55555", tenant_id=self.device.tenant_id, is_pwd=True)
        GuestCard.objects.create(guest=self.guest, card=card, is_active=True)
        self.device.device_profile_id = self.NON_DEFAULT_PROFILE_ID
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

    def test_pin_to_card_number(self):
        self.assertEqual(pin_to_card_number(123456), "01 02 03 04 05 06")
        self.assertEqual(pin_to_card_number("908172"), "09 00 08 01 07 02")
        self.assertEqual(pin_to_card_number("111111"), "01 01 01 01 01 01")

    @patch("access_manager.tasks.send_rpc.prepare_rpc_request", wraps=prepare_rpc_request)
    @patch("access_manager.tasks.send_rpc.connect_to_rabbitmq")
    @patch("access_manager.tasks.send_rpc.send_to_rabbitmq")
    def test_pwd_sent_as_card_on_default_profile_device(self, mock_send_rabbitmq, mock_connect_rabbitmq, mock_prepare):
        # Device 47aef21b uses the "default" device profile in the fixtures.
        self.assertEqual(self.device.device_profile.name.lower(), "default")

        send_rpc_request(
            device_id=self.device_id,
            cards=["123456"],
            access=1,
            guest_id=self.guest_id,
            is_pwd=True,
        )

        mock_prepare.assert_called_once_with(
            self.device_id, ["01 02 03 04 05 06"], 1, self.guest_id, None, is_pwd=False
        )
        rpc_data = mock_send_rabbitmq.call_args[0][1]["data"]["data"]
        self.assertEqual(rpc_data["method"], "writeRFID")
        self.assertIn("01 02 03 04 05 06", [p["cardNumber"] for p in rpc_data["params"]])

    @patch("access_manager.tasks.send_rpc.prepare_rpc_request", wraps=prepare_rpc_request)
    @patch("access_manager.tasks.send_rpc.connect_to_rabbitmq")
    @patch("access_manager.tasks.send_rpc.send_to_rabbitmq")
    def test_pwd_deactivation_sent_as_card_on_default_profile_device(
        self, mock_send_rabbitmq, mock_connect_rabbitmq, mock_prepare
    ):
        send_rpc_request(
            device_id=self.device_id,
            cards=["908172"],
            access=0,
            guest_id=self.guest_id,
            is_pwd=True,
        )

        mock_prepare.assert_called_once_with(
            self.device_id, ["09 00 08 01 07 02"], 0, self.guest_id, None, is_pwd=False
        )
        rpc_data = mock_send_rabbitmq.call_args[0][1]["data"]["data"]
        self.assertEqual(rpc_data["method"], "writeRFID")

    @patch("access_manager.tasks.send_rpc.connect_to_rabbitmq")
    @patch("access_manager.tasks.send_rpc.send_to_rabbitmq")
    def test_rfid_not_skipped_on_default_profile_device(self, mock_send_rabbitmq, mock_connect_rabbitmq):
        # RFID (is_pwd=False) on a Default-profile device must keep its existing behaviour.
        result = send_rpc_request(
            device_id=self.device_id,
            cards=["65 28 23 12"],
            access=1,
            guest_id=self.guest_id,
            is_pwd=False,
        )

        self.assertNotIn("skipped_default_profile", result)
        mock_send_rabbitmq.assert_called_once()


class SyncDevicesTaskPwdGroupingTest(TestCase):
    fixtures = FIXTURES

    def setUp(self):
        self.device_id = "47aef21b-6cc9-4ec5-8573-1a6f491940c0"
        self.device = Device.objects.get(id=self.device_id)
        self.tenant_id = self.device.tenant_id

    @patch("access_manager.tasks.sync_device.sync_device_card_group.delay")
    def test_pwd_rows_dispatch_with_is_pwd_true(self, mock_dispatch):
        from access_manager.tasks.sync_device import sync_devices_task

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

        calls = mock_dispatch.call_args_list
        pwd_calls = [c for c in calls if c.args[3]]
        rfid_calls = [c for c in calls if not c.args[3]]

        self.assertEqual(len(pwd_calls), 1)
        self.assertEqual(pwd_calls[0].args[1], ["77777"])
        self.assertEqual(len(rfid_calls), 1)
        self.assertIn("11 22 33 44", rfid_calls[0].args[1])

    @patch("access_manager.tasks.sync_device.sync_device_card_group.delay")
    def test_replays_original_source_and_user(self, mock_dispatch):
        from access_manager.tasks.sync_device import sync_devices_task

        karina_id = "e1fcc1ff-cce1-47e9-9951-88665815a9bb"
        card = Card.objects.create(number="55 66 77 88", tenant_id=self.tenant_id)
        NeedSyncDevice.objects.create(
            card=card,
            device=self.device,
            need_sync=True,
            updated_by_id=karina_id,
            additional_info={"message_params": {"access": 0, "source": Guest.SOURCE.FIAS}},
        )

        sync_devices_task(tenant_id=self.tenant_id)

        mock_dispatch.assert_called_once()
        self.assertEqual(mock_dispatch.call_args.kwargs, {"source": Guest.SOURCE.FIAS, "user_id": karina_id})

    @patch("access_manager.tasks.sync_device.sync_device_card_group.delay")
    def test_manual_sync_records_requesting_user_as_roomio(self, mock_dispatch):
        from access_manager.tasks.sync_device import sync_devices_task

        karina_id = "e1fcc1ff-cce1-47e9-9951-88665815a9bb"
        requester_id = str(User.objects.exclude(id=karina_id).first().id)
        card = Card.objects.create(number="55 66 77 88", tenant_id=self.tenant_id)
        NeedSyncDevice.objects.create(
            card=card,
            device=self.device,
            need_sync=True,
            updated_by_id=karina_id,
            additional_info={"message_params": {"access": 0, "source": Guest.SOURCE.FIAS}},
        )

        sync_devices_task(tenant_id=self.tenant_id, user_id=requester_id)

        mock_dispatch.assert_called_once()
        self.assertEqual(mock_dispatch.call_args.kwargs, {"source": Guest.SOURCE.ROOMIO, "user_id": requester_id})

    @patch("access_manager.tasks.sync_device.send_rpc_request", return_value={"success": True})
    def test_requests_queued_without_source_replay_as_auto(self, mock_send):
        from access_manager.tasks.sync_device import sync_device_card_group

        sync_device_card_group(self.device_id, ["55 66 77 88"], 0)

        self.assertEqual(mock_send.call_args.kwargs["source"], Guest.SOURCE.AUTO)
        self.assertIsNone(mock_send.call_args.kwargs["user"])


class SyncDeviceCardGroupClearsOnlySentRowsTest(TestCase):
    fixtures = FIXTURES

    def setUp(self):
        self.device = Device.objects.get(id="47aef21b-6cc9-4ec5-8573-1a6f491940c0")
        tenant_id = self.device.tenant_id
        NeedSyncDevice.objects.filter(device=self.device).delete()
        self.rows = {}
        for number, is_pwd, access in (
            ("11 22 33 44", False, 1),
            ("55 66 77 88", False, 1),
            ("99 88 77 66", False, 0),
            ("482915", True, 1),
        ):
            card = Card.objects.create(number=number, tenant_id=tenant_id, is_pwd=is_pwd)
            self.rows[number] = NeedSyncDevice.objects.create(
                card=card,
                device=self.device,
                need_sync=True,
                additional_info={"message_params": {"access": access}},
            )

    def _pending(self):
        return set(
            NeedSyncDevice.objects.filter(device=self.device, need_sync=True).values_list("card__number", flat=True)
        )

    @patch("access_manager.tasks.sync_device.send_rpc_request", return_value={"success": True})
    def test_rfid_success_clears_only_sent_cards_with_same_access(self, _):
        from access_manager.tasks.sync_device import sync_device_card_group

        sync_device_card_group(str(self.device.id), ["11 22 33 44"], 1)

        self.assertEqual(self._pending(), {"55 66 77 88", "99 88 77 66", "482915"})

    @patch("access_manager.tasks.sync_device.send_rpc_request", return_value={"success": True})
    def test_pwd_success_clears_only_that_pin(self, _):
        from access_manager.tasks.sync_device import sync_device_card_group

        sync_device_card_group(str(self.device.id), ["482915"], 1, True)

        self.assertEqual(self._pending(), {"11 22 33 44", "55 66 77 88", "99 88 77 66"})

    @patch("access_manager.tasks.sync_device.send_rpc_request", return_value={"success": False})
    def test_failure_clears_nothing(self, _):
        from access_manager.tasks.sync_device import sync_device_card_group

        sync_device_card_group(str(self.device.id), ["11 22 33 44", "55 66 77 88"], 1)

        self.assertEqual(len(self._pending()), 4)

    @patch("access_manager.tasks.sync_device.send_rpc_request", return_value={"success": True})
    def test_default_device_sends_rfid_in_one_request(self, mock_send):
        from access_manager.tasks.sync_device import sync_device_card_group

        sync_device_card_group(str(self.device.id), ["11 22 33 44", "55 66 77 88"], 1)

        mock_send.assert_called_once_with(
            str(self.device.id),
            ["11 22 33 44", "55 66 77 88"],
            1,
            user=None,
            sync=True,
            is_pwd=False,
            source=Guest.SOURCE.AUTO,
        )

    @patch("access_manager.tasks.sync_device.send_rpc_request")
    def test_non_default_device_sends_one_card_per_request(self, mock_send):
        from access_manager.tasks.sync_device import sync_device_card_group

        self.device.device_profile_id = SendRpcRequestPwdTest.NON_DEFAULT_PROFILE_ID
        self.device.save(update_fields=["device_profile"])
        mock_send.side_effect = [{"success": True}, {"success": False}]

        sync_device_card_group(str(self.device.id), ["11 22 33 44", "55 66 77 88"], 1)

        self.assertEqual(
            [c.args[1] for c in mock_send.call_args_list],
            [["11 22 33 44"], ["55 66 77 88"]],
        )
        self.assertEqual(self._pending(), {"55 66 77 88", "99 88 77 66", "482915"})


class ProcessDeviceAllCardsTest(TestCase):
    fixtures = FIXTURES

    def setUp(self):
        self.device = Device.objects.get(id="47aef21b-6cc9-4ec5-8573-1a6f491940c0")
        self.cards = ["11 22 33 44", "55 66 77 88"]

    @patch("access_manager.utilits.process_multi_devices_rpc.send_card_rpc_request", return_value={"success": True})
    @patch("access_manager.utilits.process_multi_devices_rpc.prepare_rpc_request", return_value={})
    def test_default_device_sends_all_cards_at_once(self, mock_prepare, mock_send):
        from access_manager.utilits.process_multi_devices_rpc import process_device_all_cards

        result = process_device_all_cards(self.device, self.cards, None, "connect")

        mock_prepare.assert_called_once_with(self.device.id, self.cards, 1)
        self.assertTrue(result["result"]["success"])

    @patch("access_manager.utilits.process_multi_devices_rpc.send_card_rpc_request")
    @patch("access_manager.utilits.process_multi_devices_rpc.prepare_rpc_request", return_value={})
    def test_non_default_device_sends_one_card_per_request(self, mock_prepare, mock_send):
        from access_manager.utilits.process_multi_devices_rpc import process_device_all_cards

        self.device.device_profile_id = SendRpcRequestPwdTest.NON_DEFAULT_PROFILE_ID
        self.device.save(update_fields=["device_profile"])
        self.device.refresh_from_db()
        mock_send.side_effect = [{"success": True, "message": "ok"}, {"success": False, "message": "rejected"}]

        result = process_device_all_cards(self.device, self.cards, None, "disconnect")

        self.assertEqual([c.args[1] for c in mock_prepare.call_args_list], [["11 22 33 44"], ["55 66 77 88"]])
        self.assertEqual([c.args[2] for c in mock_send.call_args_list], [["11 22 33 44"], ["55 66 77 88"]])
        self.assertFalse(result["result"]["success"])
        self.assertEqual(result["result"]["message"], "rejected")


class DispatchCardRpcOneCardPerRequestTest(TestCase):
    fixtures = FIXTURES

    def setUp(self):
        self.device = Device.objects.get(id="47aef21b-6cc9-4ec5-8573-1a6f491940c0")
        self.device_id = str(self.device.id)
        self.cards = ["65 28 23 12", "11 22 33 44"]

    def _use_non_default_profile(self):
        self.device.device_profile_id = SendRpcRequestPwdTest.NON_DEFAULT_PROFILE_ID
        self.device.save(update_fields=["device_profile"])

    @patch("access_manager.utilits.dispatch_card_rpc.send_rpc_request", return_value={"success": True})
    def test_default_device_sends_all_cards_in_one_request(self, mock_send):
        from access_manager.utilits.dispatch_card_rpc import dispatch_card_rpc

        dispatch_card_rpc(self.device_id, self.cards, 1, user="u1")

        mock_send.assert_called_once_with(self.device_id, self.cards, 1, is_pwd=False, user="u1")

    @patch("access_manager.utilits.dispatch_card_rpc.send_rpc_request")
    def test_non_default_device_sends_one_card_per_request(self, mock_send):
        from access_manager.utilits.dispatch_card_rpc import dispatch_card_rpc

        self._use_non_default_profile()
        mock_send.side_effect = [{"success": True, "message": "ok"}, {"success": False, "message": "Time out error!"}]

        result = dispatch_card_rpc(self.device_id, self.cards, 0, source=Guest.SOURCE.ROOMIO)

        self.assertEqual([c.args[1] for c in mock_send.call_args_list], [["65 28 23 12"], ["11 22 33 44"]])
        self.assertTrue(all(c.kwargs["source"] == Guest.SOURCE.ROOMIO for c in mock_send.call_args_list))
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Time out error!")
        self.assertEqual(len(result["results"]), 2)

    @patch("access_manager.utilits.dispatch_card_rpc.send_rpc_request", return_value={"success": True})
    def test_forced_is_pwd_sends_every_card_as_pin(self, mock_send):
        from access_manager.utilits.dispatch_card_rpc import dispatch_card_rpc

        self._use_non_default_profile()

        dispatch_card_rpc(self.device_id, ["48291"], 1, is_pwd=True, guest_id="g1")

        mock_send.assert_called_once_with(self.device_id, ["48291"], 1, is_pwd=True, guest_id="g1")

    @patch("access_manager.utilits.dispatch_card_rpc.send_rpc_request", return_value={"success": True})
    def test_empty_cards_still_sends_one_request(self, mock_send):
        from access_manager.utilits.dispatch_card_rpc import dispatch_card_rpc

        self._use_non_default_profile()

        dispatch_card_rpc(self.device_id, [], 0)

        mock_send.assert_called_once_with(self.device_id, [], 0, is_pwd=False)


class MergeRpcResultsTest(TestCase):
    def test_single_result_is_returned_as_is(self):
        from access_manager.utilits.merge_rpc_results import merge_rpc_results

        result = {"success": True, "message": "ok"}
        self.assertIs(merge_rpc_results([result]), result)

    def test_any_failure_fails_and_keeps_failed_fields(self):
        from access_manager.utilits.merge_rpc_results import merge_rpc_results

        merged = merge_rpc_results(
            [
                {"success": True, "message": "ok", "room": "101"},
                {"success": False, "message": "Time out error!", "room": "101", "cards": ["x"]},
            ]
        )
        self.assertFalse(merged["success"])
        self.assertEqual(merged["message"], "Time out error!")
        self.assertEqual(merged["cards"], ["x"])
        self.assertEqual(len(merged["results"]), 2)

    def test_success_deduplicates_messages(self):
        from access_manager.utilits.merge_rpc_results import merge_rpc_results

        merged = merge_rpc_results([{"success": True, "message": "ok"}, {"success": True, "message": "ok"}])
        self.assertTrue(merged["success"])
        self.assertEqual(merged["message"], "ok")

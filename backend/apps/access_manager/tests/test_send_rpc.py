from unittest.mock import Mock, patch

from django.test import TestCase

from access_manager.models import Card, CardDeviceSlot, Group, GuestCard, NeedSyncDevice, StaffCard
from access_manager.tasks.send_rpc import send_rpc_request
from main.models import Device, Guest
from shuttle.models import RPCMessage


class SendRPCRequestTest(TestCase):
    """Integration tests for send_rpc_request that test actual method implementations"""

    fixtures = (
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

    def setUp(self):
        """Set up test data using fixture data"""
        self.karina_id = "e1fcc1ff-cce1-47e9-9951-88665815a9bb"

        self.device_id = "47aef21b-6cc9-4ec5-8573-1a6f491940c0"  # DHT11 Demo Device
        self.raspberry_device_id = "a1561fb2-e031-42ce-812a-0ce84843c0f0"  # Raspberry Pi Demo Device
        self.guest_id = "5b66af57-fb27-4c26-9986-b9994e644605"  # Amigo from fixtures

        # Staff IDs from fixtures
        self.staff_id_john = "f47ac10b-58cc-4372-a567-0e02b2c3d479"  # John Doe
        self.staff_id_jane = "a47ac10b-58cc-4372-a567-0e02b2c3d480"  # Jane Smith

        # Card numbers from fixtures
        self.staff_card_number = "65 28 23 12"
        self.guest_card_number = "12 23 34 45"
        self.master_card_number = "09 87 65 98"

        # Get actual objects from fixtures
        self.device = Device.objects.get(id=self.device_id)
        self.raspberry_device = Device.objects.get(id=self.raspberry_device_id)
        self.guest = Guest.objects.get(id=self.guest_id)

        # Import Staff model here to avoid circular import
        from access_manager.models import Staff

        self.staff_john = Staff.objects.get(id=self.staff_id_john)
        self.staff_jane = Staff.objects.get(id=self.staff_id_jane)

    def test_prepare_rpc_request_functionality(self):
        """Test prepare_rpc_request creates proper RPC message structure"""
        from access_manager.utilits.prepare_rpc_request import prepare_rpc_request

        result = prepare_rpc_request(
            device_id=self.device_id, cards=[self.staff_card_number], access=1, guest_id=self.guest_id
        )

        # Check all expected keys are present
        expected_keys = [
            "message",
            "request_id",
            "room_number",
            "public_spaces",
            "staff",
            "guest",
            "device",
            "fail_response",
        ]
        for key in expected_keys:
            self.assertIn(key, result)

        # Check message structure
        message = result["message"]
        self.assertIn("targetDeviceUUID", message)
        self.assertEqual(message["topic"], "v1/gateway/rpc")
        self.assertIn("data", message)
        self.assertIn("device", message["data"])
        self.assertIn("data", message["data"])

        # Check RPC data structure
        rpc_data = message["data"]["data"]
        self.assertIn("id", rpc_data)
        self.assertEqual(rpc_data["method"], "writeRFID")
        self.assertIn("params", rpc_data)
        self.assertEqual(rpc_data["timeout"], 10000)

        # Verify RPCMessage was created
        self.assertTrue(RPCMessage.objects.filter(id=result["request_id"]).exists())

        # Check device and guest assignment
        self.assertEqual(str(result["device"].id), self.device_id)
        self.assertEqual(str(result["guest"].id), self.guest_id)
        self.assertIsNone(result["staff"])

    def test_prepare_rpc_request_with_staff(self):
        """Test prepare_rpc_request creates proper RPC message for staff"""
        from access_manager.utilits.prepare_rpc_request import prepare_rpc_request

        result = prepare_rpc_request(
            device_id=self.device_id, cards=[self.staff_card_number], access=1, staff_id=self.staff_id_john
        )

        # Check staff assignment
        self.assertEqual(str(result["staff"].id), self.staff_id_john)
        self.assertEqual(result["staff"].first_name, "John")
        self.assertEqual(result["staff"].last_name, "Doe")
        self.assertIsNone(result["guest"])

        # Check RPC params include group information
        message = result["message"]
        rpc_params = message["data"]["data"]["params"]

        # Should have card parameters with group info
        self.assertGreater(len(rpc_params), 0)
        card_param = rpc_params[2]
        self.assertEqual(card_param["cardNumber"], self.staff_card_number)
        # Should have group_type from John's Housekeeping Group (group_type=2)
        self.assertEqual(card_param["access_group"], "2")

    def test_get_device_cards_functionality(self):
        """Test get_device_cards returns correct cards for device"""
        from access_manager.utilits.get_device_cards import get_device_cards

        # Test connect=True (should include incoming cards)
        cards = get_device_cards(device_id=self.raspberry_device_id, cards=[self.guest_card_number], connect=True)

        # Should include the guest card we passed + any existing cards
        self.assertIn(self.guest_card_number, cards)

        # Test connect=False (should exclude incoming cards)
        cards_disconnect = get_device_cards(
            device_id=self.raspberry_device_id, cards=[self.guest_card_number], connect=False
        )

        # Should not include the guest card we passed
        self.assertNotIn(self.guest_card_number, cards_disconnect)

    def test_prepare_cards_functionality(self):
        """Test prepare_cards creates proper card parameters"""
        from access_manager.utilits.prepare_cards import prepare_cards

        group = Group.objects.get(pk="ee74097b-fb0a-4e7b-9cdc-10dc54eab55c")  # Housekeeping Group

        rpc_params = prepare_cards(cards=[self.staff_card_number], device=self.device, connect=1, group=group)

        self.assertEqual(len(rpc_params), 1)
        card_param = rpc_params[0]

        # Check card parameter structure
        expected_keys = ["cardNumber", "access_group", "start_time", "end_time", "weekdays", "slot_num"]
        for key in expected_keys:
            self.assertIn(key, card_param)

        self.assertEqual(card_param["cardNumber"], self.staff_card_number)
        self.assertEqual(card_param["access_group"], "2")  # group_type from fixture
        self.assertEqual(card_param["start_time"], "08:00")
        self.assertEqual(card_param["end_time"], "18:00")
        self.assertEqual(card_param["slot_num"], "2")  # From CardDeviceSlot fixture

    def test_str_to_dict_functionality(self):
        """Test str_to_dict properly converts string to dict"""
        from core.utils.str_to_dict import str_to_dict

        # Test normal JSON string
        json_str = '{"success": true, "message": "test"}'
        result = str_to_dict(json_str)
        self.assertEqual(result, {"success": True, "message": "test"})

        # Test string with escaped quotes
        escaped_str = '"{"success": true}"'
        result = str_to_dict(escaped_str)
        self.assertEqual(result, {"success": True})

        # Test already dict
        dict_input = {"success": False}
        result = str_to_dict(dict_input)
        self.assertEqual(result, dict_input)

        # Test invalid JSON
        invalid_str = "not json"
        result = str_to_dict(invalid_str)
        self.assertEqual(result, "not json")  # Should return original

    @patch("access_manager.tasks.send_rpc.connect_to_rabbitmq")
    @patch("access_manager.tasks.send_rpc.send_to_rabbitmq")
    def test_activate_guest_card_integration(self, mock_send_rabbitmq, mock_connect_rabbitmq):
        """Test full guest card activation flow"""
        mock_connect_rabbitmq.return_value = Mock()

        # Create RPC response message
        RPCMessage.objects.create(additional_info={"success": True})

        with patch("access_manager.tasks.send_rpc.RPCMessage") as mock_rpc_message:
            mock_message = Mock()
            mock_message.additional_info = '{"success": true}'
            mock_rpc_message.objects.filter.return_value.first.return_value = mock_message

            result = send_rpc_request(
                device_id=self.device_id, cards=[self.guest_card_number], access=1, guest_id=self.guest_id
            )

        # Should be successful
        self.assertTrue(result["success"])
        self.assertIn("room", result)
        self.assertIn("public_spaces", result)

        # Check that guest card was actually created/updated
        guest_card = GuestCard.objects.filter(
            guest=self.guest, card__number=self.guest_card_number, is_active=True
        ).first()
        self.assertIsNotNone(guest_card)

    @patch("access_manager.tasks.send_rpc.connect_to_rabbitmq")
    @patch("access_manager.tasks.send_rpc.send_to_rabbitmq")
    def test_deactivate_guest_card_integration(self, mock_send_rabbitmq, mock_connect_rabbitmq):
        """Test full guest card deactivation flow"""
        mock_connect_rabbitmq.return_value = Mock()

        # First ensure we have an active guest card
        card, _ = Card.objects.get_or_create(
            number=self.guest_card_number, tenant_id=self.guest.tenant_id, defaults={"is_active": True}
        )
        GuestCard.objects.get_or_create(guest=self.guest, card=card, defaults={"is_active": True})

        with patch("access_manager.tasks.send_rpc.RPCMessage") as mock_rpc_message:
            mock_message = Mock()
            mock_message.additional_info = '{"success": true}'
            mock_rpc_message.objects.filter.return_value.first.return_value = mock_message

            result = send_rpc_request(
                device_id=self.device_id,
                cards=[self.guest_card_number],
                access=0,  # Deactivate
            )

        # Should be successful
        self.assertTrue(result["success"])

        # Check that guest card was actually deactivated
        guest_card = GuestCard.objects.filter(
            guest__room=self.device.room, card__number=self.guest_card_number, is_active=True
        ).first()
        self.assertIsNone(guest_card)

    def test_device_offline_creates_need_sync(self):
        """Test that offline device creates NeedSyncDevice record"""
        # Make device offline
        self.device.status = False
        self.device.save()

        initial_sync_count = NeedSyncDevice.objects.count()

        result = send_rpc_request(
            device_id=self.device_id, cards=[self.guest_card_number], access=0, user=self.karina_id
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Device is not connected !")

        final_sync_count = NeedSyncDevice.objects.count()

        self.assertGreater(final_sync_count, initial_sync_count)

        need_sync = NeedSyncDevice.objects.filter(device=self.device, need_sync=True).last()
        self.assertIsNotNone(need_sync)
        self.assertEqual(need_sync.additional_info["message_params"]["access"], 0)

    def test_empty_cards_handling(self):
        """Test handling of empty cards list"""
        result = send_rpc_request(device_id=self.device_id, cards=[], access=1)

        self.assertTrue(result["success"])
        self.assertTrue(result["cards_empty"])
        self.assertEqual(result["message"], "Cards are not provided ! ")

    @patch("access_manager.tasks.send_rpc.connect_to_rabbitmq")
    @patch("access_manager.tasks.send_rpc.send_to_rabbitmq")
    def test_timeout_scenario(self, mock_send_rabbitmq, mock_connect_rabbitmq):
        mock_connect_rabbitmq.return_value = Mock()
        initial_sync_count = NeedSyncDevice.objects.count()

        result = send_rpc_request(device_id=self.device_id, cards=[self.guest_card_number], access=1)

        # Should fail with timeout
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Time out error!")

        # Should create NeedSyncDevice record
        final_sync_count = NeedSyncDevice.objects.count()
        self.assertGreater(final_sync_count, initial_sync_count)

    @patch("access_manager.tasks.send_rpc.connect_to_rabbitmq")
    @patch("access_manager.tasks.send_rpc.send_to_rabbitmq")
    def test_rpc_failure_handling(self, mock_send_rabbitmq, mock_connect_rabbitmq):
        """Test handling when RPC returns failure"""
        mock_connect_rabbitmq.return_value = Mock()

        with patch("access_manager.tasks.send_rpc.RPCMessage") as mock_rpc_message:
            mock_message = Mock()
            mock_message.additional_info = '{"success": false, "error": "Device error"}'
            mock_rpc_message.objects.filter.return_value.first.return_value = mock_message

            initial_sync_count = NeedSyncDevice.objects.count()

            result = send_rpc_request(
                device_id=self.device_id,
                cards=[self.guest_card_number],
                access=0,  # Deactivate
                sync=False,
            )

            # Should fail
            self.assertFalse(result["success"])

            # Should create NeedSyncDevice record for failed deactivation
            final_sync_count = NeedSyncDevice.objects.count()
            self.assertGreater(final_sync_count, initial_sync_count)

    def test_sync_mode_operation(self):
        """Test sync=True mode returns simple success"""
        with patch("access_manager.tasks.send_rpc.connect_to_rabbitmq") as mock_connect:
            with patch("access_manager.tasks.send_rpc.send_to_rabbitmq"):
                with patch("access_manager.tasks.send_rpc.RPCMessage") as mock_rpc_message:
                    mock_connect.return_value = Mock()
                    mock_message = Mock()
                    mock_message.additional_info = '{"success": true}'
                    mock_rpc_message.objects.filter.return_value.first.return_value = mock_message

                    result = send_rpc_request(
                        device_id=self.device_id, cards=[self.guest_card_number], access=1, sync=True
                    )

                    self.assertTrue(result["success"])
                    self.assertEqual(result["message"], "Operation is passed successfully! ")

    def test_card_slot_assignment(self):
        """Test that cards get proper slot assignments"""
        from access_manager.utilits.prepare_cards import find_or_assign_slot

        # # Test existing slot
        existing_slot = find_or_assign_slot("12 23 34 45", self.device, connect=False)
        self.assertEqual(existing_slot, 1)  # From fixtures

        # Test new card slot assignment
        new_card_number = "99 88 77 66"
        new_slot = find_or_assign_slot(new_card_number, self.device, connect=True)
        self.assertGreater(new_slot, 1)

        # Verify CardDeviceSlot was created
        slot_obj = CardDeviceSlot.objects.filter(card_number=new_card_number, device=self.device).first()
        self.assertIsNotNone(slot_obj)
        self.assertEqual(slot_obj.slot, new_slot)

    @patch("access_manager.tasks.send_rpc.connect_to_rabbitmq")
    @patch("access_manager.tasks.send_rpc.send_to_rabbitmq")
    def test_activate_staff_card_integration(self, mock_send_rabbitmq, mock_connect_rabbitmq):
        """Test full staff card activation flow"""
        mock_connect_rabbitmq.return_value = Mock()

        with patch("access_manager.tasks.send_rpc.RPCMessage") as mock_rpc_message:
            mock_message = Mock()
            mock_message.additional_info = '{"success": true}'
            mock_rpc_message.objects.filter.return_value.first.return_value = mock_message

            result = send_rpc_request(
                device_id=self.device_id, cards=[self.staff_card_number], access=1, staff_id=self.staff_id_john
            )

        # Should be successful
        self.assertTrue(result["success"])
        self.assertIn("room", result)
        self.assertIn("public_spaces", result)
        self.assertIn("device", result)
        self.assertEqual(result["message"], "Successfully activated staff card.")

        # Check that staff card was actually created/updated
        staff_card = StaffCard.objects.filter(
            staff=self.staff_john, card__number=self.staff_card_number, is_active=True
        ).first()
        self.assertIsNotNone(staff_card)

    @patch("access_manager.tasks.send_rpc.connect_to_rabbitmq")
    @patch("access_manager.tasks.send_rpc.send_to_rabbitmq")
    def test_deactivate_staff_card_integration(self, mock_send_rabbitmq, mock_connect_rabbitmq):
        """Test full staff card deactivation flow"""
        mock_connect_rabbitmq.return_value = Mock()

        # First ensure we have an active staff card
        card, _ = Card.objects.get_or_create(
            number=self.staff_card_number, tenant_id=self.staff_john.tenant_id, defaults={"is_active": True}
        )
        StaffCard.objects.get_or_create(staff=self.staff_john, card=card, defaults={"is_active": True})

        with patch("access_manager.tasks.send_rpc.RPCMessage") as mock_rpc_message:
            mock_message = Mock()
            mock_message.additional_info = '{"success": true}'
            mock_rpc_message.objects.filter.return_value.first.return_value = mock_message

            result = send_rpc_request(
                device_id=self.device_id,
                cards=[self.staff_card_number],
                access=0,  # Deactivate
                staff_id=self.staff_id_john,
            )

        # Should be successful
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Card is deactivated.")

        # Check that staff card was actually deactivated
        staff_card = StaffCard.objects.filter(
            staff=self.staff_john, card__number=self.staff_card_number, is_active=True
        ).first()
        self.assertIsNone(staff_card)

    def test_staff_group_parameters(self):
        """Test staff card parameters include correct group information"""
        from access_manager.utilits.prepare_cards import prepare_cards

        # John is in Housekeeping Group (group_type=2, 08:00-18:00, all_days)
        rpc_params = prepare_cards(
            cards=[self.staff_card_number], device=self.device, connect=1, group=self.staff_john.group
        )

        self.assertEqual(len(rpc_params), 1)
        card_param = rpc_params[0]

        self.assertEqual(card_param["cardNumber"], self.staff_card_number)
        self.assertEqual(card_param["access_group"], "2")  # Housekeeping group_type
        self.assertEqual(card_param["start_time"], "08:00")
        self.assertEqual(card_param["end_time"], "18:00")
        self.assertEqual(card_param["weekdays"], ["1", "2", "3", "4", "5", "6", "7"])  # all_days

        # Jane is in Engineering Group (group_type=3, 09:00-17:00, weekdays)
        rpc_params_jane = prepare_cards(
            cards=["new_card_123"], device=self.device, connect=1, group=self.staff_jane.group
        )

        jane_param = rpc_params_jane[0]
        self.assertEqual(jane_param["access_group"], "3")  # Engineering group_type
        self.assertEqual(jane_param["start_time"], "09:00")
        self.assertEqual(jane_param["end_time"], "17:00")
        # Should have weekday indexes (not all days)
        self.assertNotEqual(jane_param["weekdays"], ["1", "2", "3", "4", "5", "6", "7"])

    @patch("access_manager.tasks.send_rpc.connect_to_rabbitmq")
    @patch("access_manager.tasks.send_rpc.send_to_rabbitmq")
    @patch("access_manager.tasks.send_rpc.activate_staff_card")
    def test_staff_card_activation_failure_handling(self, mock_activate, mock_send_rabbitmq, mock_connect_rabbitmq):
        """Test staff card activation with simulated failure"""
        mock_connect_rabbitmq.return_value = Mock()

        with patch("access_manager.tasks.send_rpc.RPCMessage") as mock_rpc_message:
            mock_message = Mock()
            mock_message.additional_info = '{"success": true}'
            mock_rpc_message.objects.filter.return_value.first.return_value = mock_message

            mock_activate.return_value = {"success": False, "message": "Staff card activation failed"}

            result = send_rpc_request(
                device_id=self.device_id, cards=[self.staff_card_number], access=1, staff_id=self.staff_id_john
            )
            self.assertFalse(result["success"])
            self.assertEqual(result["message"], "Staff card activation failed")


class SendRPCRequestCeleryTest(TestCase):
    """Test Celery task functionality"""

    fixtures = (
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

    def setUp(self):
        self.device_id = "47aef21b-6cc9-4ec5-8573-1a6f491940c0"
        self.guest_card_number = "65 28 23 12"
        self.staff_card_number = "12 23 34 45"
        self.guest_id = "5b66af57-fb27-4c26-9986-b9994e644605"
        self.staff_id_john = "f47ac10b-58cc-4372-a567-0e02b2c3d479"

    @patch("access_manager.tasks.send_rpc.send_rpc_request.retry")
    @patch("access_manager.tasks.send_rpc.connect_to_rabbitmq")
    def test_celery_task_retry_on_exception(self, mock_connect, mock_retry):
        """Test that Celery task retries on exceptions"""
        mock_connect.side_effect = Exception("Connection failed")
        mock_retry.side_effect = Exception("Max retries exceeded")

        with self.assertRaises(Exception):
            send_rpc_request(device_id=self.device_id, cards=[self.guest_card_number], access=1)

        # Should have attempted retry
        mock_retry.assert_called_once()

    @patch("access_manager.tasks.send_rpc.connect_to_rabbitmq")
    @patch("access_manager.tasks.send_rpc.send_to_rabbitmq")
    def test_celery_task_success_execution(self, mock_send, mock_connect):
        """Test successful Celery task execution"""
        mock_connect.return_value = Mock()

        with patch("access_manager.tasks.send_rpc.RPCMessage") as mock_rpc_message:
            mock_message = Mock()
            mock_message.additional_info = '{"success": true}'
            mock_rpc_message.objects.filter.return_value.first.return_value = mock_message

            # Execute as Celery task
            result = send_rpc_request.apply(
                kwargs={
                    "device_id": self.device_id,
                    "cards": [self.guest_card_number],
                    "access": 1,
                    "guest_id": self.guest_id,
                }
            )

            # Should complete successfully
            self.assertTrue(result.successful())
            task_result = result.get()
            self.assertTrue(task_result["success"])

    def test_celery_task_configuration(self):
        """Test Celery task is properly configured"""
        # Check task decorator configuration
        self.assertTrue(hasattr(send_rpc_request, "retry"))
        self.assertEqual(send_rpc_request.autoretry_for, (Exception,))
        self.assertEqual(send_rpc_request.retry_kwargs["max_retries"], 3)
        self.assertEqual(send_rpc_request.retry_kwargs["countdown"], 60)

    @patch("access_manager.tasks.send_rpc.connect_to_rabbitmq")
    @patch("access_manager.tasks.send_rpc.send_to_rabbitmq")
    def test_async_task_execution(self, mock_send, mock_connect):
        """Test asynchronous task execution"""
        mock_connect.return_value = Mock()

        with patch("access_manager.tasks.send_rpc.RPCMessage") as mock_rpc_message:
            mock_message = Mock()
            mock_message.additional_info = '{"success": true}'
            mock_rpc_message.objects.filter.return_value.first.return_value = mock_message

            # Execute asynchronously
            result = send_rpc_request(
                device_id=self.device_id, cards=[self.guest_card_number], access=1, guest_id=self.guest_id
            )
            result = result
            self.assertTrue(result["success"])

    @patch("access_manager.tasks.send_rpc.connect_to_rabbitmq")
    @patch("access_manager.tasks.send_rpc.send_to_rabbitmq")
    def test_celery_staff_task_execution(self, mock_send, mock_connect):
        """Test Celery task execution with staff card"""
        mock_connect.return_value = Mock()

        with patch("access_manager.tasks.send_rpc.RPCMessage") as mock_rpc_message:
            mock_message = Mock()
            mock_message.additional_info = '{"success": true}'
            mock_rpc_message.objects.filter.return_value.first.return_value = mock_message

            # Execute as Celery task with staff
            result = send_rpc_request.apply(
                kwargs={
                    "device_id": self.device_id,
                    "cards": [self.staff_card_number],
                    "access": 1,
                    "staff_id": self.staff_id_john,
                }
            )

            # Should complete successfully
            self.assertTrue(result.successful())
            task_result = result.get()
            self.assertTrue(task_result["success"])
            self.assertEqual(task_result["message"], "Successfully activated staff card.")


class SendRPCRequestRealDataTest(TestCase):
    """Test with actual fixture data to ensure real-world compatibility"""

    fixtures = (
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

    def test_fixture_data_integrity(self):
        """Verify fixture data is loaded correctly"""
        # Check cards from fixtures
        staff_card = Card.objects.get(number="12 23 34 45")
        self.assertEqual(staff_card.additional_info["type"], "staff")

        guest_card = Card.objects.get(number="65 28 23 12")
        self.assertEqual(guest_card.additional_info["type"], "guest")

        master_card = Card.objects.get(number="09 87 65 98")
        self.assertEqual(master_card.additional_info["type"], "master")

        # Check groups
        housekeeping_group = Group.objects.get(name="Housekeeping Group")
        self.assertEqual(housekeeping_group.group_type, 2)
        self.assertEqual(str(housekeeping_group.start_time), "08:00:00")

        engineering_group = Group.objects.get(name="Engineering Group")
        self.assertEqual(engineering_group.group_type, 3)
        self.assertIn("monday", engineering_group.week_days)

    @patch("access_manager.tasks.send_rpc.connect_to_rabbitmq")
    @patch("access_manager.tasks.send_rpc.send_to_rabbitmq")
    def test_real_fixture_card_activation(self, mock_send, mock_connect):
        """Test activation using real fixture card data"""
        mock_connect.return_value = Mock()

        device_id = "47aef21b-6cc9-4ec5-8573-1a6f491940c0"
        guest_id = "5b66af57-fb27-4c26-9986-b9994e644605"

        # Use actual card from fixtures
        card_number = "65 28 23 12"  # guest card from fixture

        with patch("access_manager.tasks.send_rpc.RPCMessage") as mock_rpc_message:
            mock_message = Mock()
            mock_message.additional_info = '{"success": true}'
            mock_rpc_message.objects.filter.return_value.first.return_value = mock_message

            result = send_rpc_request(device_id=device_id, cards=[card_number], access=1, guest_id=guest_id)

            self.assertTrue(result["success"])
            self.assertIn("message", result)

            # Verify the card exists and is properly processed
            card = Card.objects.get(number=card_number)
            self.assertTrue(card.is_active)

    def test_card_slot_with_fixture_data(self):
        """Test card slot assignment with fixture data"""
        device_id = "47aef21b-6cc9-4ec5-8573-1a6f491940c0"
        card_number = "12 23 34 45"  # Has slot 1 in fixture

        device = Device.objects.get(id=device_id)

        from access_manager.utilits.prepare_cards import find_or_assign_slot

        # Should return existing slot from fixture
        slot = find_or_assign_slot(card_number, device, connect=False)
        self.assertEqual(slot, 1)

        # Verify the CardDeviceSlot exists
        slot_obj = CardDeviceSlot.objects.get(card_number=card_number, device=device)
        self.assertEqual(slot_obj.slot, 1)

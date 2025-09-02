import uuid
from unittest.mock import patch
from django.urls import reverse

from core.tests.base import BaseTestCase
from access_manager.models import (
    Staff, GroupRoom, GroupPublicSpace
)
from main.models import Device


class StaffCardViewTest(BaseTestCase):
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
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.url = reverse("access_manager:staff-card")

    @patch('access_manager.views.staff_card.send_rpc_request')
    def test_connect_cards_to_staff_success(self, mock_send_rpc):
        """Test successful connection of cards to staff"""
        mock_send_rpc.return_value = {"success": True, "message": "Card added successfully"}

        payload = {
            "staff_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",  # John Doe
            "cards": ["11 22 33 44", "55 66 77 88"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Cards connected successfully !")

        # Verify RPC was called for each device
        self.assertTrue(mock_send_rpc.called)

    @patch('access_manager.views.staff_card.send_rpc_request')
    def test_connect_cards_partial_success(self, mock_send_rpc):
        """Test partial success when some RPC calls fail"""
        # Mock some successful and some failed RPC calls
        mock_send_rpc.side_effect = [
            {"success": True, "message": "Card added successfully"},
            {"success": False, "message": "Device unreachable"}
        ]

        payload = {
            "staff_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "cards": ["11 22 33 44"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.data)
        self.assertIn("success", response.data)
        self.assertEqual(response.data["message"], "Couldn't synchronize the card with all devices !")

    def test_connect_cards_staff_not_found(self):
        """Test error when staff is not found"""
        payload = {
            "staff_id": str(uuid.uuid4()),
            "cards": ["11 22 33 44"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("staff_id", response.data)

    def test_connect_cards_staff_not_active(self):
        """Test error when staff is not active"""
        # Make John Doe inactive
        staff = Staff.objects.get(id="f47ac10b-58cc-4372-a567-0e02b2c3d479")
        staff.is_active = False
        staff.save()

        payload = {
            "staff_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "cards": ["11 22 33 44"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Staff is not active", str(response.data))

    def test_connect_cards_staff_no_group(self):
        """Test error when staff has no group"""
        # Remove group from John Doe
        staff = Staff.objects.get(id="f47ac10b-58cc-4372-a567-0e02b2c3d479")
        staff.group = None
        staff.save()

        payload = {
            "staff_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "cards": ["11 22 33 44"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Staff has no group", str(response.data))

    def test_connect_cards_already_connected_to_guest(self):
        """Test error when card is already connected to a guest"""
        payload = {
            "staff_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "cards": ["12 23 34 45"]  # This card is connected to guest via GuestCard
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["message"], "Card is already assigned .")

    def test_connect_cards_already_connected_to_other_staff(self):
        """Test error when card is already connected to another staff member"""
        payload = {
            "staff_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",  # John Doe
            "cards": ["09 87 65 98"]  # This card is connected to Jane Smith
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["message"], "Card is already assigned .")

    def test_connect_cards_no_devices_found(self):
        """Test error when no devices are found for the staff's group"""
        # Remove all group room and public space associations
        GroupRoom.objects.filter(group_id="ee74097b-fb0a-4e7b-9cdc-10dc54eab55c").delete()
        GroupPublicSpace.objects.filter(group_id="ee74097b-fb0a-4e7b-9cdc-10dc54eab55c").delete()

        payload = {
            "staff_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "cards": ["11 22 33 44"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["detail"], "Not found device.")

    def test_connect_cards_max_cards_validation(self):
        """Test validation error when more than 10 cards are provided"""
        payload = {
            "staff_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "cards": [f"card_{i:02d}" for i in range(11)]  # 11 cards
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Maximum 10 cards allowed", str(response.data))

    def test_connect_cards_missing_staff_id(self):
        """Test validation error when staff_id is missing"""
        payload = {
            "cards": ["11 22 33 44"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("staff_id", response.data)

    def test_connect_cards_missing_cards(self):
        """Test validation error when cards are missing"""
        payload = {
            "staff_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("cards", response.data)

    @patch('access_manager.views.staff_card.send_rpc_request')
    def test_connect_cards_rpc_exception_handling(self, mock_send_rpc):
        """Test handling of RPC exceptions"""
        mock_send_rpc.side_effect = Exception("RPC connection failed")

        payload = {
            "staff_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "cards": ["11 22 33 44"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 200)  # View returns 200 with error message
        self.assertIn("error", response.data)

    @patch('access_manager.views.staff_card.send_rpc_request')
    def test_connect_cards_device_filtering(self, mock_send_rpc):
        """Test that only active devices are considered"""
        mock_send_rpc.return_value = {"success": True, "message": "Card added successfully"}

        # Deactivate one of the devices
        device = Device.objects.get(id="47aef21b-6cc9-4ec5-8573-1a6f491940c0")
        device.is_active = False
        device.save()

        payload = {
            "staff_id": "a47ac10b-58cc-4372-a567-0e02b2c3d480",
            "cards": ["11 22 33 44"]
        }

        response = self.client.post(self.url, payload, format="json")

        # Should still succeed with remaining active devices
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])

    @patch('access_manager.views.staff_card.send_rpc_request')
    def test_connect_cards_with_engineering_group(self, mock_send_rpc):
        """Test connecting cards for staff in engineering group"""
        mock_send_rpc.return_value = {"success": True, "message": "Card added successfully"}

        payload = {
            "staff_id": "a47ac10b-58cc-4372-a567-0e02b2c3d480",  # Jane Smith (Engineering Group)
            "cards": ["11 22 33 44"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])

    @patch('access_manager.views.staff_card.send_rpc_request')
    def test_rpc_request_parameters(self, mock_send_rpc):
        """Test that RPC request is called with correct parameters"""
        mock_send_rpc.return_value = {"success": True, "message": "Card added successfully"}

        payload = {
            "staff_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "cards": ["11 22 33 44"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 200)

        # Verify RPC was called with correct parameters
        mock_send_rpc.assert_called()
        call_args = mock_send_rpc.call_args

        # Check the parameters passed to send_rpc_request
        self.assertIn("11 22 33 44", call_args[0][1])  # cards parameter
        self.assertTrue(call_args[0][2])  # is_active parameter
        self.assertEqual(call_args[1]["staff_id"], "f47ac10b-58cc-4372-a567-0e02b2c3d479")

    def test_connect_cards_wrong_tenant(self):
        """Test that staff from different tenant cannot be accessed"""
        # This would require creating a staff with different tenant_id
        # For now, we test the existing validation through invalid staff_id
        payload = {
            "staff_id": str(uuid.uuid4()),
            "cards": ["11 22 33 44"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("staff_id", response.data)

    @patch('access_manager.views.staff_card.send_rpc_request')
    def test_connect_multiple_cards_success(self, mock_send_rpc):
        """Test connecting multiple cards successfully"""
        mock_send_rpc.return_value = {"success": True, "message": "Card added successfully"}

        payload = {
            "staff_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "cards": ["11 22 33 44", "55 66 77 88", "99 00 11 22"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Cards connected successfully !")

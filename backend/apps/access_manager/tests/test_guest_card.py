from unittest.mock import patch
from django.urls import reverse

from core.tests.base import BaseTestCase
from access_manager.models import (
    GuestPublicSpace
)
from main.models import Device


class GuestCardViewTest(BaseTestCase):
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
        self.url = reverse("access_manager:guest-card")

    @patch('access_manager.tasks.send_rpc.send_rpc_request')
    def test_connect_cards_to_guest_success(self, mock_send_rpc):
        """Test successful connection of cards to guest"""
        mock_send_rpc.return_value = {"success": True, "message": "Card added successfully"}

        payload = {
            "guest_id": "5b66af57-fb27-4c26-9986-b9994e644605",  # Amigo
            "cards": ["11 22 33 44", "55 66 77 88"],
            "public_spaces": ["ad09aa20-77b8-457a-bfc4-5dee69790243"]  # Lobby
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Cards connected successfully !")

        # Verify RPC was called
        self.assertTrue(mock_send_rpc.called)

        # Verify GuestPublicSpace was created
        self.assertTrue(
            GuestPublicSpace.objects.filter(
                guest_id="5b66af57-fb27-4c26-9986-b9994e644605",
                public_space_id="ad09aa20-77b8-457a-bfc4-5dee69790243"
            ).exists()
        )

    @patch('access_manager.tasks.send_rpc.send_rpc_request')
    def test_connect_cards_without_public_spaces(self, mock_send_rpc):
        """Test connecting cards without specifying public spaces"""
        mock_send_rpc.return_value = {"success": True, "message": "Card added successfully"}

        payload = {
            "guest_id": "5b66af57-fb27-4c26-9986-b9994e644605",
            "cards": ["11 22 33 44"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])

    @patch('access_manager.tasks.send_rpc.send_rpc_request')
    def test_connect_cards_partial_success(self, mock_send_rpc):
        """Test partial success when some RPC calls fail"""
        mock_send_rpc.side_effect = [
            {"success": True, "message": "Card added successfully"},
            {"success": False, "message": "Device unreachable"}
        ]

        payload = {
            "guest_id": "5b66af57-fb27-4c26-9986-b9994e644605",
            "cards": ["11 22 33 44"],
            "public_spaces": ["ad09aa20-77b8-457a-bfc4-5dee69790243"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.data)
        self.assertIn("success", response.data)
        self.assertEqual(response.data["message"], "Couldn't synchronize the card with all devices !")

    def test_connect_cards_already_connected_to_staff(self):
        """Test error when card is already connected to staff"""
        payload = {
            "guest_id": "5b66af57-fb27-4c26-9986-b9994e644605",
            "cards": ["65 28 23 12"],  # This card is connected to staff via StaffCard
            "public_spaces": ["ad09aa20-77b8-457a-bfc4-5dee69790243"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["message"], "Card is already assigned .")

    def test_connect_cards_already_connected_to_other_guest(self):
        """Test error when card is already connected to another guest"""
        payload = {
            "guest_id": "52d8ba26-6fac-463b-a131-c16410e42ede",  # Alexandr Slaven
            "cards": ["12 23 34 45"],  # This card is connected to Amigo via GuestCard
            "public_spaces": ["ad09aa20-77b8-457a-bfc4-5dee69790243"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["message"], "Card is already assigned .")

    def test_connect_cards_same_guest_allowed(self):
        """Test that connecting cards to the same guest is allowed"""
        with patch('access_manager.tasks.send_rpc.send_rpc_request') as mock_send_rpc:
            mock_send_rpc.return_value = {"success": True, "message": "Card added successfully"}

            payload = {
                "guest_id": "5b66af57-fb27-4c26-9986-b9994e644605",  # Amigo (same as in fixture)
                "cards": ["12 23 34 45"],  # Card already connected to this guest
                "public_spaces": ["ad09aa20-77b8-457a-bfc4-5dee69790243"]
            }

            response = self.client.post(self.url, payload, format="json")

            # Should succeed because it's the same guest
            self.assertEqual(response.status_code, 200)

    def test_connect_cards_no_devices_found(self):
        """Test error when no devices are found"""
        # Use a guest that has no associated devices
        payload = {
            "guest_id": "52d8ba26-6fac-463b-a131-c16410e42ede",  # Alexandr Slaven in room 102
            "cards": ["11 22 33 44"],
            "public_spaces": []  # No public spaces and room has no devices
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["message"], "Not found device.")

    def test_connect_cards_max_cards_validation(self):
        """Test validation error when more than 10 cards are provided"""
        payload = {
            "guest_id": "5b66af57-fb27-4c26-9986-b9994e644605",
            "cards": [f"card_{i:02d}" for i in range(11)],  # 11 cards
            "public_spaces": ["ad09aa20-77b8-457a-bfc4-5dee69790243"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Maximum 10 cards allowed", str(response.data))

    def test_connect_cards_missing_guest_id(self):
        """Test validation error when guest_id is missing"""
        payload = {
            "cards": ["11 22 33 44"],
            "public_spaces": ["ad09aa20-77b8-457a-bfc4-5dee69790243"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("guest_id", response.data)

    def test_connect_cards_missing_cards(self):
        """Test validation error when cards are missing"""
        payload = {
            "guest_id": "5b66af57-fb27-4c26-9986-b9994e644605",
            "public_spaces": ["ad09aa20-77b8-457a-bfc4-5dee69790243"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("cards", response.data)


    def test_connect_cards_invalid_serializer_data(self):
        """Test error when serializer receives invalid data"""
        payload = None  # Invalid data

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400)

    @patch('access_manager.tasks.send_rpc.send_rpc_request')
    def test_connect_cards_exception_handling(self, mock_send_rpc):
        """Test handling of exceptions during processing"""
        mock_send_rpc.side_effect = Exception("Database connection failed")

        payload = {
            "guest_id": "5b66af57-fb27-4c26-9986-b9994e644605",
            "cards": ["11 22 33 44"],
            "public_spaces": ["ad09aa20-77b8-457a-bfc4-5dee69790243"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["message"], "Server error !")
        self.assertIn("error", response.data)

    @patch('access_manager.tasks.send_rpc.send_rpc_request')
    def test_rpc_request_parameters(self, mock_send_rpc):
        """Test that RPC request is called with correct parameters"""
        mock_send_rpc.return_value = {"success": True, "message": "Card added successfully"}

        payload = {
            "guest_id": "5b66af57-fb27-4c26-9986-b9994e644605",
            "cards": ["11 22 33 44"],
            "public_spaces": ["ad09aa20-77b8-457a-bfc4-5dee69790243"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 200)

        # Verify RPC was called with correct parameters
        mock_send_rpc.assert_called()
        call_args = mock_send_rpc.call_args

        # Check the parameters passed to send_rpc_request
        self.assertIn("11 22 33 44", call_args[0][1])  # cards parameter
        self.assertEqual(call_args[0][2], 1)  # is_active parameter (1 for guest)
        self.assertEqual(call_args[1]["guest_id"], "5b66af57-fb27-4c26-9986-b9994e644605")

    @patch('access_manager.tasks.send_rpc.send_rpc_request')
    def test_device_filtering_query(self, mock_send_rpc):
        """Test the device filtering query logic"""
        mock_send_rpc.return_value = {"success": True, "message": "Card added successfully"}

        payload = {
            "guest_id": "5b66af57-fb27-4c26-9986-b9994e644605",  # Guest in room 101
            "cards": ["11 22 33 44"],
            "public_spaces": ["ad09aa20-77b8-457a-bfc4-5dee69790243"]  # Lobby
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])

    @patch('access_manager.tasks.send_rpc.send_rpc_request')
    def test_multiple_public_spaces(self, mock_send_rpc):
        """Test connecting cards with multiple public spaces"""
        mock_send_rpc.return_value = {"success": True, "message": "Card added successfully"}

        payload = {
            "guest_id": "5b66af57-fb27-4c26-9986-b9994e644605",
            "cards": ["11 22 33 44"],
            "public_spaces": [
                "ad09aa20-77b8-457a-bfc4-5dee69790243",  # Lobby
                "ad09aa20-77b8-457a-bfc4-5dee69790242"  # Conference Room
            ]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])

        # Verify both GuestPublicSpace relationships were created
        for public_space_id in payload["public_spaces"]:
            self.assertTrue(
                GuestPublicSpace.objects.filter(
                    guest_id="5b66af57-fb27-4c26-9986-b9994e644605",
                    public_space_id=public_space_id
                ).exists()
            )

    @patch('access_manager.tasks.send_rpc.send_rpc_request')
    def test_connect_multiple_cards_success(self, mock_send_rpc):
        """Test connecting multiple cards successfully"""
        mock_send_rpc.return_value = {"success": True, "message": "Card added successfully"}

        payload = {
            "guest_id": "5b66af57-fb27-4c26-9986-b9994e644605",
            "cards": ["11 22 33 44", "55 66 77 88", "99 00 11 22"],
            "public_spaces": ["ad09aa20-77b8-457a-bfc4-5dee69790243"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Cards connected successfully !")

    def test_incorrect_validated_data_handling(self):
        """Test handling when validated_data is not dict or None"""
        with patch('access_manager.serializers.guest_card.GuestCardRequestSerializer.is_valid', return_value=True):
            with patch('access_manager.serializers.guest_card.GuestCardRequestSerializer.validated_data',
                       new_callable=lambda: None):
                payload = {
                    "guest_id": "5b66af57-fb27-4c26-9986-b9994e644605",
                    "cards": ["11 22 33 44"]
                }

                response = self.client.post(self.url, payload, format="json")

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["message"], "Incorrect data!")

    @patch('access_manager.tasks.send_rpc.send_rpc_request')
    def test_device_inactive_filtering(self, mock_send_rpc):
        """Test that inactive devices are not included"""
        mock_send_rpc.return_value = {"success": True, "message": "Card added successfully"}

        # Deactivate all devices to test the filtering
        Device.objects.all().update(is_active=False)

        payload = {
            "guest_id": "5b66af57-fb27-4c26-9986-b9994e644605",
            "cards": ["11 22 33 44"],
            "public_spaces": ["ad09aa20-77b8-457a-bfc4-5dee69790243"]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["message"], "Not found device.")
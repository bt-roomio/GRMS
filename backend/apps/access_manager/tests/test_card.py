import uuid
from unittest.mock import patch

from django.urls import reverse

from access_manager.models import Card, StaffCard
from core.tests.base import BaseTestCase


class CardTest(BaseTestCase):
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

    def test_list_cards_basic(self):
        url = reverse("access_manager:card-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)

    def test_list_cards_with_search(self):
        url = reverse("access_manager:card-list")
        response = self.client.get(url, {"search_field": "number", "search_value": "65 28 23 12"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_list_cards_with_staff_filter(self):
        url = reverse("access_manager:card-list")
        response = self.client.get(url, {"staff_id": "a47ac10b-58cc-4372-a567-0e02b2c3d480"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_list_cards_with_sorting(self):
        url = reverse("access_manager:card-list")
        response = self.client.get(url, {"sort_by": ["-number"]})
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url, {"sort_by": ["number"]})
        self.assertEqual(response.status_code, 200)

    def test_list_with_pagination_and_size(self):
        url = reverse("access_manager:card-list")
        response = self.client.get(url, {"page": 1, "size": 10})
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.data["results"]), 10)

    def test_create_card_success(self):
        url = reverse("access_manager:card-list")
        payload = {
            "staff_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "additional_info": {"test": "data"},
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 201)
        card_number = response.data["number"]

        self.assertTrue(
            StaffCard.objects.filter(
                card__number=card_number,
                staff_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
            ).exists()
        )

    def test_get_card_detail(self):
        url = reverse(
            "access_manager:card-detail",
            kwargs={"pk": "f3db0b43-5537-3d9e-a44b-0411ff10dcb5"},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], "f3db0b43-5537-3d9e-a44b-0411ff10dcb5")
        self.assertEqual(response.data["number"], "65 28 23 12")

    def test_get_card_detail_not_found(self):
        url = reverse("access_manager:card-detail", kwargs={"pk": str(uuid.uuid4())})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_update_card_success(self):
        url = reverse(
            "access_manager:card-detail",
            kwargs={"pk": "f3db0b26-5537-3d9e-a44b-0411ff10dcb5"},
        )
        payload = {
            "number": "12 34 23 23",
            "staff_id": "a47ac10b-58cc-4372-a567-0e02b2c3d480",
            "additional_info": {"updated": "data"},
        }
        response = self.client.put(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["additional_info"], {"updated": "data"})

    def test_update_card_not_found(self):
        url = reverse("access_manager:card-detail", kwargs={"pk": str(uuid.uuid4())})
        payload = {"additional_info": {"test": "data"}}
        response = self.client.put(url, payload, format="json")
        self.assertEqual(response.status_code, 404)

    @patch("access_manager.views.card.unplug")
    def test_delete_card_dispatches_unplug(self, mock_unplug):
        card_id = "f3db0b26-5537-3d9e-a44b-0411ff10dcb5"
        url = reverse("access_manager:card-detail", kwargs={"pk": card_id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["message"], "Card deletion started.")
        mock_unplug.delay.assert_called_once_with(card_id)

    @patch("access_manager.tasks.unplug_card.disconnect_guests")
    @patch("access_manager.tasks.unplug_card.disconnect_staff")
    def test_unplug_deactivates_card_when_no_pending_sync(self, _m_staff, _m_guests):
        from access_manager.tasks.unplug_card import unplug

        tenant_id = Card.objects.values_list("tenant_id", flat=True).first()
        card = Card.objects.create(number="90909090", tenant_id=tenant_id, is_active=True)

        result = unplug(str(card.id))

        self.assertTrue(result)
        card.refresh_from_db()
        self.assertFalse(card.is_active)

    @patch("access_manager.tasks.unplug_card.disconnect_guests")
    @patch("access_manager.tasks.unplug_card.disconnect_staff")
    def test_unplug_keeps_card_active_when_pending_sync(self, _m_staff, _m_guests):
        from access_manager.models import NeedSyncDevice
        from access_manager.tasks.unplug_card import unplug
        from main.models import Device

        tenant_id = Card.objects.values_list("tenant_id", flat=True).first()
        card = Card.objects.create(number="80808080", tenant_id=tenant_id, is_active=True)
        device_id = Device.objects.values_list("id", flat=True).first()
        NeedSyncDevice.objects.create(card=card, device_id=device_id, need_sync=True)

        result = unplug(str(card.id))

        self.assertFalse(result)
        card.refresh_from_db()
        self.assertTrue(card.is_active)

    def test_delete_card_not_found(self):
        url = reverse("access_manager:card-detail", kwargs={"pk": str(uuid.uuid4())})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)

    @patch("access_manager.serializers.card.send_rpc_request")
    def test_disconnect_card_success(self, mock_send_rpc):
        mock_send_rpc.return_value = {"success": True}
        url = reverse("access_manager:disconnect-card")
        payload = {"card_id": "f3db0b26-5537-3d9e-a44b-0411ff10dcb5"}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Card is deactivated !")

    def test_disconnect_card_not_found(self):
        url = reverse("access_manager:disconnect-card")
        payload = {"card_id": str(uuid.uuid4())}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], "Active guest card not found !")

    def test_disconnect_card_validation_error(self):
        url = reverse("access_manager:disconnect-card")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("card_id", response.data)

    @patch("access_manager.tasks.send_rpc.send_rpc_request")
    def test_disconnect_card_rpc_failure(self, mock_send_rpc):
        mock_send_rpc.return_value = {"success": False, "message": "RPC failed"}
        url = reverse("access_manager:disconnect-card")
        payload = {"card_id": "456e7890-e12b-34d5-a678-901234567def"}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])

from django.urls import reverse

from rest_framework import status

from core.tests.base import BaseTestCase
from main.models import Device, Room, RoomType


class RoomFromConfTestCase(BaseTestCase):
    fixtures = (
        "tenant.yaml",
        "tenant_profile.yaml",
        "users.yaml",
        "roles_permissions.yaml",
        "device_without_room.yaml",
        "device_profile.yaml",
    )

    def setUp(self):
        super().setUp()
        self.url = reverse("main:room-from-conf-list")
        self.device = Device.objects.get(pk="47aef21b-6cc9-4ec5-8573-1a6f491940c0")
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"

    def test_create_rooms_from_conf_success(self):
        payload = {
            "rooms": [
                {"number": 101, "floor": "1", "block": "A", "type": "Deluxe", "devices": ["DHT11 Demo Device"]},
                {"number": 102, "floor": "1", "block": "A", "devices": ["FF:EE:DD:CC:BB:AA"]},
                {"number": 103, "floor": "2", "block": "B"},
            ]
        }

        response = self.client.post(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertEqual(len(data["rooms"]), 2)
        self.assertEqual(len(data["errors"]), 0)

        self.assertEqual(len(data["device_errors"]), 1)
        self.assertEqual(data["device_errors"][0]["device_mac"], "FF:EE:DD:CC:BB:AA")

        self.assertTrue(Room.objects.filter(number=101, tenant=self.tenant_id).exists())
        self.assertTrue(Room.objects.filter(number=102, tenant=self.tenant_id).exists())
        self.assertTrue(Room.objects.filter(number=103, tenant=self.tenant_id).exists())

        # RoomType should be created
        self.assertTrue(RoomType.objects.filter(title="Deluxe", tenant=self.tenant_id).exists())

        # Device should now be assigned to room 101
        self.device.refresh_from_db()
        self.assertEqual(self.device.room.number, 101)

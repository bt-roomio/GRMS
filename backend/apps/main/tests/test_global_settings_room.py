from datetime import timedelta

from django.contrib.auth import authenticate
from django.urls import reverse
from django.utils import timezone

from rest_framework_simplejwt.tokens import RefreshToken

from core.tests.base import BaseTestCase
from main.models import Device, DeviceProfile, GlobalSettingsTemplate, Room, RoomType
from shuttle.models import AttributeKv

TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"
TENANT_2_ID = "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc"
NON_EXISTENT_ID = "11111111-1111-1111-1111-111111111111"


class GlobalSettingsRoomTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)
        self.url = reverse("main:global-settings-room-list")
        self.standard = RoomType.objects.create(title="Standard", tenant_id=TENANT_ID)
        self.lux = RoomType.objects.create(title="Lux", tenant_id=TENANT_ID)
        self.profile = DeviceProfile.objects.create(name="default", type="DEFAULT", tenant_id=TENANT_ID)

        self.room_101 = Room.objects.create(number="101", floor="1", block="1", type=self.standard, tenant_id=TENANT_ID)
        self.room_201 = Room.objects.create(number="201", floor="2", block="1", type=self.lux, tenant_id=TENANT_ID)
        self.room_b101 = Room.objects.create(number="B101", floor="1", block="2", tenant_id=TENANT_ID)
        Room.objects.create(number="301", floor="3", block="1", tenant_id=TENANT_ID, active=False)
        Room.objects.create(number="101", floor="1", block="1", tenant_id=TENANT_2_ID)
        # Rooms without devices are hidden, so every room gets a device that is never shown first.
        for room in (self.room_101, self.room_201, self.room_b101):
            self.create_device(f"Base-{room.number}", room, created_at=100)

    def create_device(self, name, room, created_at, **kwargs):
        return Device.objects.create(
            name=name,
            type="DEFAULT",
            tenant_id=TENANT_ID,
            device_profile=self.profile,
            room=room,
            created_at=created_at,
            **kwargs,
        )

    def fetch(self, room_types=None, blocks=None):
        params = {}
        if room_types is not None:
            params["room_types"] = ",".join(str(room_type.id) for room_type in room_types)
        if blocks is not None:
            params["blocks"] = blocks
        return self.get(self.url, params)

    def numbers(self, response):
        return [room["number"] for room in response.data]

    def test_list_returns_active_rooms_of_own_tenant(self):
        response = self.fetch()
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.numbers(response), ["101", "201", "B101"])

    def test_response_shape(self):
        self.create_device("RCU-101", self.room_101, created_at=2)
        first = self.create_device("Lock-101", self.room_101, created_at=1)

        response = self.fetch(room_types=[self.standard])
        assert response.data is not None
        self.assertEqual(
            response.data,
            [
                {
                    "id": str(self.room_101.id),
                    "number": "101",
                    "floor": "1",
                    "block": "1",
                    "room_type": {"id": self.standard.id, "title": "Standard"},
                    "device": {"id": str(first.id), "name": "Lock-101"},
                    "template": None,
                }
            ],
        )

    def test_primary_device_comes_first(self):
        self.create_device("Old", self.room_101, created_at=1)
        primary = self.create_device("Primary", self.room_101, created_at=2, additional_info={"primary": True})
        self.create_device("Inactive", self.room_101, created_at=0, is_active=False)

        response = self.fetch()
        assert response.data is not None
        self.assertEqual(response.data[0]["device"], {"id": str(primary.id), "name": "Primary"})

    def test_room_without_type(self):
        response = self.fetch(blocks=["2:1"])
        assert response.data is not None
        self.assertIsNone(response.data[0]["room_type"])

    def test_rooms_without_active_devices_are_hidden(self):
        empty = Room.objects.create(number="102", floor="1", block="1", tenant_id=TENANT_ID)
        only_inactive = Room.objects.create(number="103", floor="1", block="1", tenant_id=TENANT_ID)
        self.create_device("Old-103", only_inactive, created_at=1, is_active=False)

        response = self.fetch()
        self.assertNotIn(empty.number, self.numbers(response))
        self.assertNotIn(only_inactive.number, self.numbers(response))
        self.assertEqual(self.numbers(response), ["101", "201", "B101"])

    def test_filter_by_room_types(self):
        response = self.fetch(room_types=[self.standard, self.lux])
        self.assertEqual(self.numbers(response), ["101", "201"])

    def test_filter_by_blocks(self):
        response = self.fetch(blocks=["1:2", "2:1"])
        self.assertEqual(self.numbers(response), ["201", "B101"])

    def test_filters_are_combined(self):
        response = self.fetch(room_types=[self.lux], blocks=["1:1"])
        self.assertEqual(self.numbers(response), [])

    def test_invalid_room_type_id_is_rejected(self):
        response = self.get(self.url, {"room_types": ["not-a-uuid"]})
        self.assertEqual(response.status_code, 400)

    def test_filter_by_whole_block(self):
        response = self.fetch(blocks=["1"])
        self.assertEqual(self.numbers(response), ["101", "201"])

    def test_repeated_room_types_param(self):
        response = self.get(self.url, {"room_types": [str(self.standard.id), str(self.lux.id)]})
        self.assertEqual(self.numbers(response), ["101", "201"])

    def test_filter_by_floors_in_every_block(self):
        response = self.fetch(blocks=[":1"])
        self.assertEqual(self.numbers(response), ["101", "B101"])

    def test_floors_in_every_block_or_whole_block(self):
        response = self.fetch(blocks=[":2", "2"])
        self.assertEqual(self.numbers(response), ["201", "B101"])

    def test_repeated_floor_rules_are_merged(self):
        response = self.fetch(blocks=[":1", ":2"])
        self.assertEqual(self.numbers(response), ["101", "201", "B101"])

    def test_invalid_blocks_are_rejected(self):
        for raw in (":", " : , "):
            with self.subTest(raw=raw):
                response = self.get(self.url, {"blocks": raw})
                self.assertEqual(response.status_code, 400)

    def test_search(self):
        self.create_device("RCU-B101", self.room_b101, created_at=1)
        self.create_device("Lock-201", self.room_201, created_at=1)
        cases = (
            ("number", "b1", ["B101"]),
            ("number", "01", ["101", "201", "B101"]),
            ("floor", "2", ["201"]),
            ("block", "2", ["B101"]),
            ("room_type", "LUX", ["201"]),
            ("device", "rcu", ["B101"]),
        )
        for field, value, numbers in cases:
            with self.subTest(field=field, value=value):
                response = self.get(self.url, {"search_field": field, "search_value": value})
                self.assertEqual(self.numbers(response), numbers)

    def test_search_by_device_uses_the_shown_device(self):
        self.create_device("RCU-101", self.room_101, created_at=1)
        self.create_device("Lock-101", self.room_101, created_at=2)
        response = self.get(self.url, {"search_field": "device", "search_value": "lock"})
        self.assertEqual(self.numbers(response), [])

    def test_search_is_combined_with_filters(self):
        response = self.get(self.url, {"blocks": "1", "search_field": "number", "search_value": "1"})
        self.assertEqual(self.numbers(response), ["101", "201"])

    def test_search_params_are_validated(self):
        for params in (
            {"search_field": "number"},
            {"search_value": "1"},
            {"search_field": "label", "search_value": "1"},
        ):
            with self.subTest(params=params):
                self.assertEqual(self.get(self.url, params).status_code, 400)

    def apply_template_id(self, device, template_id, ts):
        AttributeKv.objects.create(
            entity=device,
            entity_type="DEVICE",
            attribute_type=AttributeKv.SERVER_SCOPE,
            attribute_key="template_id",
            str_v=str(template_id),
            last_update_ts=ts,
        )

    def template_of_101(self):
        response = self.fetch(room_types=[self.standard])
        assert response.data is not None
        return response.data[0]["template"]

    def test_template_up_to_date(self):
        template = GlobalSettingsTemplate.objects.create(name="Default", tenant_id=TENANT_ID)
        device = self.create_device("RCU-101", self.room_101, created_at=1)
        self.apply_template_id(device, template.id, ts=int(template.config_updated_at.timestamp() * 1000) + 1)

        self.assertEqual(self.template_of_101(), {"id": template.id, "name": "Default", "status": "up_to_date"})

    def test_template_outdated_after_config_change(self):
        template = GlobalSettingsTemplate.objects.create(name="Default", tenant_id=TENANT_ID)
        device = self.create_device("RCU-101", self.room_101, created_at=1)
        self.apply_template_id(device, template.id, ts=int(template.config_updated_at.timestamp() * 1000))
        template.config_updated_at += timedelta(seconds=1)
        template.save()

        self.assertEqual(self.template_of_101()["status"], "outdated")

    def test_template_deleted(self):
        device = self.create_device("RCU-101", self.room_101, created_at=1)
        foreign = GlobalSettingsTemplate.objects.create(name="Foreign", tenant_id=TENANT_2_ID)
        for template_id in (NON_EXISTENT_ID, foreign.id, "not-a-uuid"):
            with self.subTest(template_id=template_id):
                AttributeKv.objects.filter(entity=device).delete()
                self.apply_template_id(device, template_id, ts=1)
                self.assertEqual(self.template_of_101(), {"id": str(template_id), "name": None, "status": "deleted"})

    def test_template_is_taken_from_the_shown_device(self):
        template = GlobalSettingsTemplate.objects.create(name="Default", tenant_id=TENANT_ID)
        other = self.create_device("Lock-101", self.room_101, created_at=2)
        self.create_device("RCU-101", self.room_101, created_at=1)
        self.apply_template_id(other, template.id, ts=int(timezone.now().timestamp() * 1000))

        self.assertIsNone(self.template_of_101())

    def test_user_without_perms_is_forbidden(self):
        user = authenticate(email="romeo@gmail.com", password="password")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")  # ty: ignore
        self.assertEqual(self.get(self.url).status_code, 403)

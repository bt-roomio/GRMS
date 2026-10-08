import uuid

from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Device, Room, RoomType
from shuttle.models import Relation, TsKvDictionary, TsKvLatest


class DeviceFromConfTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "customer.yaml",
        "room.yaml",
        "device_profile.yaml",
        "device.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.url = reverse("main:device-from-conf-list")
        self.gateway_id = "c3d4e5f6-a7b8-9012-cdef-123456789012"
        self.tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"

    # ── helpers ──────────────────────────────────────────────────────────
    def _valid_payload(self, **overrides):
        """Return a valid camelCase payload, with optional overrides."""
        payload = {
            "gatewayId": self.gateway_id,
            "devices": [
                {"macAddress": "AA:BB:CC:DD:EE:01", "addressMapId": 1},
                {"macAddress": "AA:BB:CC:DD:EE:02", "addressMapId": 1},
            ],
            "addressMaps": [
                {
                    "addressMapId": 1,
                    "timeseries": [{"tag": "temperature"}, {"tag": "humidity"}],
                    "attributes": [{"tag": "firmware_version"}],
                    "attributeUpdates": [{"tag": "config_param"}],
                }
            ],
        }
        payload.update(overrides)
        return payload

    # ── success cases ────────────────────────────────────────────────────
    def test_post_success(self):
        """POST with valid payload creates devices and returns 200."""
        payload = self._valid_payload()
        response = self.client.post(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["gateway_id"]), self.gateway_id)
        self.assertEqual(len(response.data["devices"]), 2)

    def test_post_creates_new_devices(self):
        """POST creates Device records for new MAC addresses."""
        payload = self._valid_payload()
        self.client.post(self.url, data=payload, format="json")

        self.assertTrue(Device.objects.filter(name="AA:BB:CC:DD:EE:01", tenant_id=self.tenant_id).exists())
        self.assertTrue(Device.objects.filter(name="AA:BB:CC:DD:EE:02", tenant_id=self.tenant_id).exists())

    def test_post_creates_ts_kv_dictionary_entries(self):
        """POST creates TsKvDictionary entries for timeseries tags."""
        payload = self._valid_payload()
        self.client.post(self.url, data=payload, format="json")

        self.assertTrue(TsKvDictionary.objects.filter(key="temperature").exists())
        self.assertTrue(TsKvDictionary.objects.filter(key="humidity").exists())

    def test_post_creates_ts_kv_latest(self):
        """POST creates TsKvLatest entries for each device-timeseries pair."""
        payload = self._valid_payload()
        self.client.post(self.url, data=payload, format="json")

        dev1 = Device.objects.get(name="AA:BB:CC:DD:EE:01", tenant_id=self.tenant_id)
        ts_entries = TsKvLatest.objects.filter(entity_id=dev1.id)
        # 2 timeseries tags → 2 TsKvLatest entries per device
        self.assertEqual(ts_entries.count(), 2)

    def test_post_creates_relations_to_gateway(self):
        """POST creates Relation records linking devices to the gateway."""
        payload = self._valid_payload()
        self.client.post(self.url, data=payload, format="json")

        relations = Relation.objects.filter(from_id=self.gateway_id, relation_type="Created")
        self.assertEqual(relations.count(), 2)

    def test_post_idempotent_devices(self):
        """POST twice with same MACs does not duplicate Device records."""
        payload = self._valid_payload()
        self.client.post(self.url, data=payload, format="json")
        self.client.post(self.url, data=payload, format="json")

        count = Device.objects.filter(name="AA:BB:CC:DD:EE:01", tenant_id=self.tenant_id).count()
        self.assertEqual(count, 1)

    def test_post_invalid_gateway_id(self):
        """POST with non-existent gateway_id returns 400."""
        payload = self._valid_payload(gatewayId=str(uuid.uuid4()))
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("gateway_id", response.data)

    def test_post_non_gateway_device(self):
        """POST with a device that is not a gateway returns 400."""
        # 47aef21b... is a normal device without additional_info.gateway=true
        payload = self._valid_payload(gatewayId="47aef21b-6cc9-4ec5-8573-1a6f491940c0")
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_post_no_devices_returns_400(self):
        """POST with empty devices list returns 400."""
        payload = self._valid_payload(devices=[])
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_post_devices_missing_mac_address_key(self):
        """POST with devices lacking macAddress key returns 400."""
        payload = self._valid_payload(devices=[{"addressMapId": 1}])
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_post_missing_gateway_id(self):
        """POST without gatewayId returns 400."""
        payload = {
            "devices": [{"macAddress": "AA:BB:CC:DD:EE:01", "addressMapId": 1}],
            "addressMaps": [{"addressMapId": 1}],
        }
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    # ── rooms ────────────────────────────────────────────────────────────
    def _room_payload(self):
        return self._valid_payload(
            devices=[
                {"macAddress": "AA:BB:CC:DD:EE:01", "addressMapId": 1, "roomNumber": "201", "roomType": "STD"},
                {"macAddress": "AA:BB:CC:DD:EE:02", "addressMapId": 1, "roomNumber": "101", "roomType": "SUITE"},
                {"macAddress": "AA:BB:CC:DD:EE:03", "addressMapId": 1},
            ]
        )

    def test_post_uses_given_floor_and_block(self):
        """POST creates new rooms with the optional floor/block when provided."""
        payload = self._valid_payload(
            devices=[
                {
                    "macAddress": "AA:BB:CC:DD:EE:01",
                    "addressMapId": 1,
                    "roomNumber": "501",
                    "roomType": "STD",
                    "floor": "5F",
                    "block": "B",
                }
            ]
        )
        self.client.post(self.url, data=payload, format="json")

        room = Room.objects.get(tenant_id=self.tenant_id, number="501")
        self.assertEqual((room.floor, room.block), ("5F", "B"))

    def test_post_response_includes_room(self):
        """Response returns each device's room number, floor, block and type."""
        response = self.client.post(self.url, data=self._room_payload(), format="json")

        devices = {d["mac_address"]: d for d in response.data["devices"]}
        linked = devices["AA:BB:CC:DD:EE:01"]
        self.assertEqual(
            (linked["room_number"], linked["floor"], linked["block"], linked["room_type"]),
            ("201", "2", "A", "STD"),
        )
        self.assertNotIn("room_number", devices["AA:BB:CC:DD:EE:03"])

    def test_post_creates_rooms_and_room_types(self):
        """POST creates room types and new rooms, and links devices to them."""
        response = self.client.post(self.url, data=self._room_payload(), format="json")
        self.assertEqual(response.status_code, 200)

        room = Room.objects.get(tenant_id=self.tenant_id, number="201")
        self.assertEqual((room.floor, room.block, room.type.title), ("2", "A", "STD"))
        self.assertTrue(RoomType.objects.filter(tenant_id=self.tenant_id, title="SUITE").exists())

        dev = Device.objects.get(tenant_id=self.tenant_id, name="AA:BB:CC:DD:EE:01")
        self.assertEqual(dev.room_id, room.id)
        self.assertIsNone(Device.objects.get(tenant_id=self.tenant_id, name="AA:BB:CC:DD:EE:03").room_id)

    def test_post_reuses_existing_room(self):
        """POST links devices to an existing room with the same number and sets its type."""
        self.client.post(self.url, data=self._room_payload(), format="json")

        self.assertEqual(Room.objects.filter(tenant_id=self.tenant_id, number="101").count(), 1)
        room = Room.objects.get(pk="df77f910-2dcd-45cf-b6be-054c744561a7")
        self.assertEqual(room.type.title, "SUITE")
        self.assertEqual(Device.objects.get(tenant_id=self.tenant_id, name="AA:BB:CC:DD:EE:02").room_id, room.id)

    def test_post_rooms_idempotent(self):
        """POST twice does not duplicate rooms or room types."""
        self.client.post(self.url, data=self._room_payload(), format="json")
        self.client.post(self.url, data=self._room_payload(), format="json")

        self.assertEqual(Room.objects.filter(tenant_id=self.tenant_id, number="201").count(), 1)
        self.assertEqual(RoomType.objects.filter(tenant_id=self.tenant_id, title="STD").count(), 1)

    def test_post_snake_case_payload(self):
        """POST accepts a snake_case payload and links devices to rooms."""
        payload = {
            "gateway_id": self.gateway_id,
            "devices": [
                {"mac_address": "AA:BB:CC:DD:EE:01", "address_map_id": 1, "room_number": "201", "room_type": "STD"}
            ],
            "address_maps": [{"address_map_id": 1, "timeseries": [{"tag": "temperature"}]}],
        }
        response = self.client.post(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, 200)
        room = Room.objects.get(tenant_id=self.tenant_id, number="201")
        self.assertEqual(Device.objects.get(tenant_id=self.tenant_id, name="AA:BB:CC:DD:EE:01").room_id, room.id)

    # ── Permission / Auth ────────────────────────────────────────────────
    def test_post_unauthenticated_rejected(self):
        """Unauthenticated request is rejected."""
        self.client.credentials()
        response = self.client.post(self.url, data=self._valid_payload(), format="json")
        self.assertIn(response.status_code, (401, 403))

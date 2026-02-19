import uuid

from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Device
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

    # ── Permission / Auth ────────────────────────────────────────────────
    def test_post_unauthenticated_rejected(self):
        """Unauthenticated request is rejected."""
        self.client.credentials()
        response = self.client.post(self.url, data=self._valid_payload(), format="json")
        self.assertIn(response.status_code, (401, 403))

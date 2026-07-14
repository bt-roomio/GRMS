import uuid

from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Device
from shuttle.models import AttributeKv, Relation, TsKvDictionary, TsKvLatest


class KnxDeviceFromConfTest(BaseTestCase):
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
        self.url = reverse("main:knx-device-from-conf-list")
        self.gateway_id = "c3d4e5f6-a7b8-9012-cdef-123456789012"
        self.tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"

    # ── helpers ──────────────────────────────────────────────────────────
    def _valid_payload(self, **overrides):
        """Return a valid KNX (camelCase) payload, with optional overrides."""
        payload = {
            "gatewayId": self.gateway_id,
            "clients": [
                {
                    "devices": [
                        {
                            "deviceInfo": {
                                "deviceNameExpression": "Room100",
                                "deviceProfileNameExpression": "default",
                            },
                            "timeseries": [
                                {
                                    "key": "temperature",
                                    "type": "temperature",
                                    "groupAddress": "1/2/3",
                                },
                                {
                                    "key": "humidity",
                                    "type": "percent",
                                    "groupAddress": "1/2/4",
                                },
                            ],
                            "attributes": [
                                {
                                    "key": "firmware_version",
                                    "type": "counter",
                                    "groupAddress": "1/2/5",
                                }
                            ],
                            "attributeUpdates": [
                                {
                                    "key": "config_param",
                                    "type": "switch",
                                    "groupAddress": "1/2/6",
                                }
                            ],
                        },
                        {
                            "deviceInfo": {
                                "deviceNameExpression": "Room101",
                                "deviceProfileNameExpression": "default",
                            },
                            "timeseries": [
                                {
                                    "key": "temperature",
                                    "type": "temperature",
                                    "groupAddress": "2/2/3",
                                },
                                {
                                    "key": "humidity",
                                    "type": "percent",
                                    "groupAddress": "2/2/4",
                                },
                            ],
                            "attributes": [],
                            "attributeUpdates": [],
                        },
                    ]
                }
            ],
        }
        payload.update(overrides)
        return payload

    # ── success cases ────────────────────────────────────────────────────
    def test_post_success(self):
        response = self.client.post(self.url, data=self._valid_payload(), format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["gateway_id"]), self.gateway_id)
        self.assertEqual(len(response.data["devices"]), 2)

    def test_post_creates_new_devices(self):
        self.client.post(self.url, data=self._valid_payload(), format="json")
        self.assertTrue(Device.objects.filter(name="Room100", tenant_id=self.tenant_id).exists())
        self.assertTrue(Device.objects.filter(name="Room101", tenant_id=self.tenant_id).exists())

    def test_post_creates_ts_kv_dictionary_entries(self):
        self.client.post(self.url, data=self._valid_payload(), format="json")
        self.assertTrue(TsKvDictionary.objects.filter(key="temperature").exists())
        self.assertTrue(TsKvDictionary.objects.filter(key="humidity").exists())

    def test_post_creates_ts_kv_latest(self):
        self.client.post(self.url, data=self._valid_payload(), format="json")
        dev = Device.objects.get(name="Room100", tenant_id=self.tenant_id)
        self.assertEqual(TsKvLatest.objects.filter(entity_id=dev.id).count(), 2)

    def test_post_creates_attributes(self):
        self.client.post(self.url, data=self._valid_payload(), format="json")
        dev = Device.objects.get(name="Room100", tenant_id=self.tenant_id)
        self.assertTrue(
            AttributeKv.objects.filter(
                entity_id=dev.id,
                attribute_type="CLIENT_SCOPE",
                attribute_key="firmware_version",
            ).exists()
        )
        self.assertTrue(
            AttributeKv.objects.filter(
                entity_id=dev.id,
                attribute_type="SHARED_SCOPE",
                attribute_key="config_param",
            ).exists()
        )

    def test_post_creates_relations_to_gateway(self):
        self.client.post(self.url, data=self._valid_payload(), format="json")
        relations = Relation.objects.filter(from_id=self.gateway_id, relation_type="Created")
        self.assertEqual(relations.count(), 2)

    def test_post_idempotent_devices(self):
        self.client.post(self.url, data=self._valid_payload(), format="json")
        self.client.post(self.url, data=self._valid_payload(), format="json")
        self.assertEqual(Device.objects.filter(name="Room100", tenant_id=self.tenant_id).count(), 1)

    def test_post_flattens_multiple_clients(self):
        payload = self._valid_payload()
        payload["clients"].append(
            {
                "devices": [
                    {
                        "deviceInfo": {
                            "deviceNameExpression": "Room200",
                            "deviceProfileNameExpression": "default",
                        },
                        "timeseries": [
                            {
                                "key": "temperature",
                                "type": "temperature",
                                "groupAddress": "3/2/3",
                            }
                        ],
                    }
                ]
            }
        )
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Device.objects.filter(name="Room200", tenant_id=self.tenant_id).exists())

    # ── validation / auth ────────────────────────────────────────────────
    def test_post_invalid_gateway_id(self):
        payload = self._valid_payload(gatewayId=str(uuid.uuid4()))
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("gateway_id", response.data)

    def test_post_non_gateway_device(self):
        payload = self._valid_payload(gatewayId="47aef21b-6cc9-4ec5-8573-1a6f491940c0")
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_post_no_devices_returns_400(self):
        payload = self._valid_payload(clients=[{"devices": []}])
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_post_missing_gateway_id(self):
        payload = self._valid_payload()
        payload.pop("gatewayId")
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_post_unauthenticated_rejected(self):
        self.client.credentials()
        response = self.client.post(self.url, data=self._valid_payload(), format="json")
        self.assertIn(response.status_code, (401, 403))

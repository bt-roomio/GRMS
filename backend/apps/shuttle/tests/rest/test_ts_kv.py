import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Device


class ShuttleTsKvApiTests(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "customer.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "room.yaml",
        "device_profile.yaml",
        "device.yaml",
        "ts_dictionary.yaml",
        "ts_kv.yaml",
        "ts_kv_latest.yaml",
    )

    def setUp(self):
        # DHT11 Demo Device (in Room 101), Raspberry Pi Demo Device, Room 101, Tenant main
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.dev_room_47 = uuid.UUID("47aef21b-6cc9-4ec5-8573-1a6f491940c0")
        self.dev_room_pi = uuid.UUID("a1561fb2-e031-42ce-812a-0ce84843c0f0")

    def test_tskv_list_entity_id_ok(self):
        url = reverse(
            "shuttle:ts-kv-list-view",
            kwargs={"entity_type": "DEVICE", "entity_id": str(self.dev_room_47)},
        )
        params = {
            "keys": ["humidity", "temperature"],
            "start_ts": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
            "end_ts": datetime.now(timezone.utc).isoformat(),
            "interval": 60,
            "agg": "Min",
            "limit": 100,
        }
        resp = self.client.get(url, params, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data.get("temperature"), list)
        self.assertIsInstance(resp.data.get("humidity"), list)

    def test_tskv_list_device_not_found(self):
        url = reverse(
            "shuttle:ts-kv-list-view",
            kwargs={"entity_type": "DEVICE", "entity_id": str(uuid.uuid4())},
        )
        params = {
            "keys": ["humidity"],
            "start_ts": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "end_ts": datetime.now(timezone.utc).isoformat(),
            "interval": 60,
            "agg": "Min",
            "limit": 50,
        }
        resp = self.client.get(url, params, format="json")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.data.get("detail"), "Not found device.")

    def test_tskv_list_missing_required_params(self):
        url = reverse(
            "shuttle:ts-kv-list-view",
            kwargs={"entity_type": "DEVICE", "entity_id": str(self.dev_room_47)},
        )
        # Missing required 'start_ts'/'end_ts'
        params = {"keys": ["humidity"]}
        resp = self.client.get(url, params, format="json")
        self.assertEqual(resp.status_code, 400)

    @patch("shuttle.views.ts_kv.TsKv")
    def test_export_tskv_excel_not_found(self, mock_tskv):
        url = reverse("shuttle:telemetry-export")

        device = Device.objects.get(pk=self.dev_room_47)
        payload = {
            "device": str(device.pk),
            "keys": ["humidity"],
            "all_tags": False,
            "start_ts": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "end_ts": datetime.now(timezone.utc).isoformat(),
            "page": 1,
            "size": 15,
            "sort_by": ["-ts"],
        }

        mock_manager = MagicMock()
        mock_by_tenant = MagicMock()
        mock_qs = MagicMock()
        mock_qs.exists.return_value = False

        mock_by_tenant.tag_logs.return_value = mock_qs
        mock_manager.by_tenant.return_value = mock_by_tenant
        mock_tskv.objects = mock_manager

        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.data.get("detail"), "Not found.")

    @patch("shuttle.views.ts_kv.get_space")
    @patch("shuttle.views.ts_kv.TsKv")
    def test_export_tskv_excel_ok(self, mock_tskv, mock_get_space):
        url = reverse("shuttle:telemetry-export")

        device = Device.objects.get(pk=self.dev_room_47)
        start_ts = datetime.now(timezone.utc) - timedelta(hours=2)
        end_ts = datetime.now(timezone.utc)

        payload = {
            "device": str(device.pk),
            "keys": ["humidity", "temperature"],
            "all_tags": False,
            "start_ts": start_ts.isoformat(),
            "end_ts": end_ts.isoformat(),
            "page": 1,
            "size": 15,
            "sort_by": ["-ts"],
        }

        mock_get_space.return_value = ["Floor 1 / Block 1", "Room 101"]

        records = [
            {"ts": start_ts + timedelta(minutes=30), "key_name": "humidity", "value": "55"},
            {"ts": start_ts + timedelta(minutes=60), "key_name": "temperature", "value": "24.2"},
        ]
        mock_qs = MagicMock()
        mock_qs.exists.return_value = True
        mock_qs.__iter__.return_value = iter(records)

        mock_manager = MagicMock()
        mock_by_tenant = MagicMock()
        mock_by_tenant.tag_logs.return_value = mock_qs
        mock_manager.by_tenant.return_value = mock_by_tenant

        def filter_side_effect(**kwargs):
            class _QS:
                def first(self_inner):
                    key_name = kwargs.get("key__key")
                    if key_name == "humidity":
                        return SimpleNamespace(bool_v=None, str_v=None, long_v=55, dbl_v=None, json_v=None)
                    if key_name == "temperature":
                        return SimpleNamespace(bool_v=None, str_v=None, long_v=None, dbl_v=24.2, json_v=None)
                    return None

            return _QS()

        mock_manager.filter.side_effect = filter_side_effect
        mock_tskv.objects = mock_manager

        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn('attachment; filename="tag_logs_export.xlsx"', resp["Content-Disposition"])
        content = b"".join(resp.streaming_content) if hasattr(resp, "streaming_content") else resp.content
        self.assertGreater(len(content), 1000)

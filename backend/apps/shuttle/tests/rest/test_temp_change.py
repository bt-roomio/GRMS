import uuid
from datetime import datetime
from datetime import timezone as py_tz
from unittest.mock import patch

from django.urls import reverse

from core.tests.base import BaseTestCase
from shuttle.models import TsKv, TsKvDictionary, TsKvLatest


class ShuttleTempApiChangeTsKvLatestTests(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "customer.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "room.yaml",
        "device_profile.yaml",
        "device.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        # device ids to see which device is connecting
        self.dev_room_47 = uuid.UUID("47aef21b-6cc9-4ec5-8573-1a6f491940c0")

    def test_empty_data_returns_400(self):
        url = reverse("shuttle:temp-api-change-ts-kv-latest", kwargs={"entity_id": str(self.dev_room_47)})
        resp = self.client.post(url, {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data.get("message"), "Empty data")

    @patch("shuttle.views.temp_change.get_mil_sec", return_value=1234567890123)
    @patch("shuttle.views.temp_change.timezone.now")
    def test_create_new_key_creates_latest_and_history(self, mock_now, mock_ms):
        url = reverse("shuttle:temp-api-change-ts-kv-latest", kwargs={"entity_id": str(self.dev_room_47)})

        fixed_dt = datetime(2025, 1, 2, 3, 4, 5, tzinfo=py_tz.utc)
        mock_now.return_value = fixed_dt

        payload = {"key": "test_temperature", "long_v": 25}
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("message"), "Success")

        key_obj = TsKvDictionary.objects.get(key="test_temperature")

        latest = TsKvLatest.objects.filter(entity_id=self.dev_room_47, key=key_obj).first()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.long_v, 25)
        self.assertEqual(latest.ts, 1234567890123)

        hist = TsKv.objects.filter(entity_id=self.dev_room_47, key=key_obj, ts=fixed_dt).first()
        self.assertIsNotNone(hist)
        self.assertEqual(hist.long_v, 25)

    @patch("shuttle.views.temp_change.get_mil_sec", side_effect=[1111111111111, 2222222222222])
    @patch("shuttle.views.temp_change.timezone.now")
    def test_second_post_updates_latest_and_appends_history(self, mock_now, mock_ms):
        url = reverse("shuttle:temp-api-change-ts-kv-latest", kwargs={"entity_id": str(self.dev_room_47)})

        first_dt = datetime(2025, 2, 1, 10, 0, 0, tzinfo=py_tz.utc)
        second_dt = datetime(2025, 2, 1, 11, 0, 0, tzinfo=py_tz.utc)

        # first call
        mock_now.return_value = first_dt
        resp1 = self.client.post(url, {"key": "room_power", "long_v": 1}, format="json")
        self.assertEqual(resp1.status_code, 200)

        key_obj = TsKvDictionary.objects.get(key="room_power")
        self.assertTrue(TsKv.objects.filter(entity_id=self.dev_room_47, key=key_obj, ts=first_dt, long_v=1).exists())
        latest1 = TsKvLatest.objects.get(entity_id=self.dev_room_47, key=key_obj)
        self.assertEqual(latest1.long_v, 1)
        self.assertEqual(latest1.ts, 1111111111111)

        # second call (updates latest, adds another TsKv row)
        mock_now.return_value = second_dt
        resp2 = self.client.post(url, {"key": "room_power", "long_v": 2}, format="json")
        self.assertEqual(resp2.status_code, 200)

        # latest updated
        latest2 = TsKvLatest.objects.get(entity_id=self.dev_room_47, key=key_obj)
        self.assertEqual(latest2.long_v, 2)
        self.assertEqual(latest2.ts, 2222222222222)

        # history appended
        self.assertTrue(TsKv.objects.filter(entity_id=self.dev_room_47, key=key_obj, ts=second_dt, long_v=2).exists())
        self.assertEqual(TsKv.objects.filter(entity_id=self.dev_room_47, key=key_obj).count(), 2)

import uuid
from unittest.mock import patch, MagicMock

from django.urls import reverse

from core.tests.base import BaseTestCase


class ShuttleLatestTsKvApiTests(BaseTestCase):
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
        "ts_kv_latest.yaml",
    )

    def setUp(self):
        # ids to see which device is connecting (by tenant/room or hotel/room)
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.tenant_main = uuid.UUID("28c81921-f78e-4864-87d2-cec674f19d1c")
        self.room_101_number = 101
        self.hoteza_hotel_id = "999"

    @patch("shuttle.views.latest_ts_kv.pagination")
    @patch("shuttle.views.latest_ts_kv.TsKvLatest")
    def test_latest_tskv_tenant_room_success(self, mock_tskv, mock_pagination):
        url = reverse(
            "shuttle:tenant-id-room-id-latest-ts-kv-list-view",
            kwargs={"tenant_id": str(self.tenant_main), "room_number": self.room_101_number},
        )
        params = {"keys": ["humidity", "temperature"], "page": 2, "size": 5}

        mock_qs = MagicMock()
        mock_tskv.objects.get_entity.return_value = mock_qs
        mock_qs.get_by_keys.return_value = ["dummy-row-1", "dummy-row-2"]
        mock_pagination.return_value = {"results": [{"k": "v"}], "page": 2, "size": 5}

        resp = self.client.get(url, params, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, {"results": [{"k": "v"}], "page": 2, "size": 5})

        mock_tskv.objects.get_entity.assert_called_once()
        mock_qs.get_by_keys.assert_called_once_with(["humidity", "temperature"])
        mock_pagination.assert_called_once()

    @patch("shuttle.views.latest_ts_kv.pagination")
    @patch("shuttle.views.latest_ts_kv.TsKvLatest")
    def test_latest_tskv_hoteza_hotel_room_success(self, mock_tskv, mock_pagination):
        url = reverse(
            "shuttle:tenant-id-room-id-latest-ts-kv-list-view",
            kwargs={"hotel_id": self.hoteza_hotel_id, "room_number": self.room_101_number},
        )
        params = {"keys": ["humidity"], "page": 1, "size": 15}

        mock_qs = MagicMock()
        mock_tskv.objects.get_entity.return_value = mock_qs
        mock_qs.get_by_keys.return_value = ["row"]
        mock_pagination.return_value = {"results": ["ok"], "page": 1, "size": 15}

        resp = self.client.get(url, params, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, {"results": ["ok"], "page": 1, "size": 15})

        mock_tskv.objects.get_entity.assert_called_once()
        mock_qs.get_by_keys.assert_called_once_with(["humidity"])
        mock_pagination.assert_called_once()

    def test_latest_tskv_missing_keys_validation(self):
        url = reverse(
            "shuttle:tenant-id-room-id-latest-ts-kv-list-view",
            kwargs={"tenant_id": str(self.tenant_main), "room_number": self.room_101_number},
        )
        resp = self.client.get(url, {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_latest_tskv_device_not_found_tenant_room(self):
        url = reverse(
            "shuttle:tenant-id-room-id-latest-ts-kv-list-view",
            kwargs={"tenant_id": str(self.tenant_main), "room_number": 99999},
        )
        resp = self.client.get(url, {"keys": ["humidity"]}, format="json")
        self.assertEqual(resp.status_code, 404)

    def test_latest_tskv_device_not_found_hoteza(self):
        url = reverse(
            "shuttle:tenant-id-room-id-latest-ts-kv-list-view",
            kwargs={"hotel_id": "does-not-exist", "room_number": 99999},
        )
        resp = self.client.get(url, {"keys": ["humidity"]}, format="json")
        self.assertEqual(resp.status_code, 404)
import uuid
from unittest.mock import patch

from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Device, Room


class ShuttleAttributesApiTests(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "customer.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "room.yaml",
        "device_profile.yaml",
        "device.yaml",
        "attribute_kv.yaml",
        "ts_dictionary.yaml",
        "ts_kv_latest.yaml",
    )

    def setUp(self):
        # DHT11 Demo Device (in Room 101), Raspberry Pi Demo Device, Room 101
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.dev_room_47 = uuid.UUID("47aef21b-6cc9-4ec5-8573-1a6f491940c0")
        self.dev_room_pi = uuid.UUID("a1561fb2-e031-42ce-812a-0ce84843c0f0")
        self.room_101 = uuid.UUID("df77f910-2dcd-45cf-b6be-054c744561a7")

    def test_get_attributes_client_scope(self):
        url = reverse(
            "shuttle:attributes-list",
            kwargs={"device_id": str(self.dev_room_47), "scope": "CLIENT_SCOPE"},
        )
        resp = self.client.get(url, {"tags": ["ip_address", "mac_address"]}, format="json")
        self.assertEqual(resp.status_code, 200)

        body = resp.data
        self.assertIn("data", body)
        self.assertIn("latestValues", body)
        self.assertIn("ip_address", body["data"])
        self.assertIn("mac_address", body["data"])
        self.assertEqual(body["data"]["ip_address"][0][1], "192.168.10.5")
        self.assertEqual(body["data"]["mac_address"][0][1], "00-1B-63-84-45-E7")
        self.assertIsInstance(body["data"]["ip_address"][0][0], int)
        self.assertIsInstance(body["latestValues"]["ip_address"], int)

    def test_get_attributes_latest_telemetry(self):
        url = reverse(
            "shuttle:attributes-list",
            kwargs={"device_id": str(self.dev_room_47), "scope": "LATEST_TELEMETRY"},
        )
        resp = self.client.get(url, {"tags": ["humidity", "temperature"]}, format="json")
        self.assertEqual(resp.status_code, 200)
        body = resp.data

        self.assertIn("humidity", body["data"])
        self.assertNotIn("temperature", body["data"])
        self.assertEqual(body["data"]["humidity"][0][1], 9999)
        self.assertIsInstance(body["latestValues"]["humidity"], int)

    @patch("shuttle.views.attributes.send_to_rabbitmq")
    @patch("shuttle.views.attributes.connect_to_rabbitmq")
    def test_post_attributes_shared_scope_sends_rabbitmq(self, mock_connect, mock_send):
        dev = Device.objects.get(pk=self.dev_room_47)
        dev.additional_info = {**(dev.additional_info or {}), "gateway": True}
        dev.save(update_fields=["additional_info"])

        url = reverse(
            "shuttle:attributes-list",
            kwargs={"device_id": str(dev.pk), "scope": "SHARED_SCOPE"},
        )
        payload = {"RemoteLoggingLevel": "DEBUG", "NewKey": "SomeValue"}
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 201)

        mock_connect.assert_called_once()
        mock_send.assert_called_once()

        sent_msg = mock_send.call_args[0][1]
        self.assertEqual(sent_msg["topic"], "v1/devices/me/attributes")
        self.assertIn("data", sent_msg)
        self.assertEqual(sent_msg["data"]["RemoteLoggingLevel"], "DEBUG")
        self.assertEqual(sent_msg["data"]["NewKey"], "SomeValue")



    @patch("shuttle.views.attributes.send_to_rabbitmq")
    @patch("shuttle.views.attributes.connect_to_rabbitmq")
    @patch("shuttle.views.attributes.prepare_mqtt_request")
    def test_attributes_change_rpc_mixed_batch(self, mock_prepare, mock_connect, mock_send):
        mock_prepare.return_value = {"request": "ok"}

        # DHT11 Demo Device (in Room 101), Raspberry Pi Demo Device
        for did in (self.dev_room_47, self.dev_room_pi):
            d = Device.objects.get(pk=did)
            d.additional_info = {**(d.additional_info or {}), "gateway": True}
            d.save(update_fields=["additional_info"])

        room = Room.objects.get(pk=self.room_101)

        url = reverse(
            "shuttle:attributes-change-view",
            kwargs={"entity_type": "Room", "entity_id": str(room.pk)},
        )
        batch = [
            {"type": "TELEMETRY", "items": {"power": 1, "brightness": 42}},
            {"type": "ATTRIBUTES", "scope": "SHARED_SCOPE", "items": {"RemoteLoggingLevel": "WARNING"}},
        ]
        resp = self.client.post(url, batch, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(mock_send.call_count, 2)
        self.assertGreaterEqual(mock_prepare.call_count, 2)

        body = resp.data
        self.assertIn("attributes", body)
        self.assertIn("telemetry", body)
        self.assertTrue(any(str(self.dev_room_47) in k or k == str(self.dev_room_47) for k in body["telemetry"].keys()))

    @patch("shuttle.views.attributes.send_to_rabbitmq")
    @patch("shuttle.views.attributes.connect_to_rabbitmq")
    def test_post_attributes_server_scope_no_rabbitmq(self, mock_connect, mock_send):
        url = reverse(
            "shuttle:attributes-list",
            kwargs={"device_id": str(self.dev_room_47), "scope": "SERVER_SCOPE"},
        )
        payload = {"SomeServerOnlyKey": "X"}
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 201)
        mock_connect.assert_not_called()
        mock_send.assert_not_called()
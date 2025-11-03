import uuid
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Device


class ShuttleJsonRpcApiTests(BaseTestCase):
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
        # DHT11 Demo Device (in Room 101), Raspberry Pi Demo Device, Room 101, Tenant main
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.dev_room_47 = uuid.UUID("47aef21b-6cc9-4ec5-8573-1a6f491940c0")
        self.dev_room_pi = uuid.UUID("a1561fb2-e031-42ce-812a-0ce84843c0f0")
        self.room_101_number = 101
        self.tenant_main = uuid.UUID("28c81921-f78e-4864-87d2-cec674f19d1c")

    @patch("shuttle.views.json_rpc.prepare_mqtt_request")
    def test_post_device_id_route_ok(self, mock_prepare):
        url = reverse("shuttle:json-rpc-view", kwargs={"device_id": str(self.dev_room_47)})
        payload = {"method": "ping", "params": [{"x": 1}], "timeout": 5000}
        mock_prepare.return_value = {"ok": True}
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, {"ok": True})
        mock_prepare.assert_called_once()
        args = mock_prepare.call_args[0]
        self.assertEqual(args[1], "ping")
        self.assertEqual(args[2], [{"x": 1}])
        self.assertAlmostEqual(args[3], 5, places=4)

    @patch("shuttle.views.json_rpc.prepare_mqtt_request")
    def test_post_tenant_room_route_ok(self, mock_prepare):
        url = reverse(
            "shuttle:tenant-id-room-id-json-rpc-view",
            kwargs={"tenant_id": str(self.tenant_main), "room_number": self.room_101_number},
        )
        payload = {"method": "ping", "params": [{"x": 2}], "timeout": 3000}
        mock_prepare.return_value = {"ok": True}
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        mock_prepare.assert_called_once()

    @patch("shuttle.views.json_rpc.prepare_mqtt_request")
    def test_post_hoteza_hotel_room_route_ok(self, mock_prepare):
        url = reverse(
            "shuttle:hoteza-hotel-id-json-rpc-view",
            kwargs={"hotel_id": "999", "room_number": self.room_101_number},
        )
        payload = {"method": "status", "params": [{}], "timeout": 2000}
        mock_prepare.return_value = {"ok": True}
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        mock_prepare.assert_called_once()

    def test_post_device_not_found(self):
        url = reverse("shuttle:json-rpc-view", kwargs={"device_id": str(uuid.uuid4())})
        payload = {"method": "ping", "params": [], "timeout": 1000}
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.data.get("detail"), "Not found device.")

    def test_post_missing_fields(self):
        url = reverse("shuttle:json-rpc-view", kwargs={"device_id": str(self.dev_room_47)})

        resp = self.client.post(url, {"params": [], "timeout": 1000}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Missing 'method'", resp.data.get("error", ""))

        resp = self.client.post(url, {"method": "ping", "timeout": 1000}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Missing 'params'", resp.data.get("error", ""))

        resp = self.client.post(url, {"method": "ping", "params": []}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Missing 'timeout'", resp.data.get("error", ""))


class ShuttlePrepareMqttRequestTests(BaseTestCase):
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
        self.dev_room_pi = uuid.UUID("a1561fb2-e031-42ce-812a-0ce84843c0f0")

    @patch("shuttle.views.json_rpc.RPCMessage")
    @patch("shuttle.views.json_rpc.Device.objects.gateway_or_none")
    @patch("shuttle.views.json_rpc.send_to_rabbitmq")
    @patch("shuttle.views.json_rpc.connect_to_rabbitmq")
    def test_prepare_mqtt_request_uses_gateway_and_returns_received_payload(
        self, mock_connect, mock_send, mock_gateway_or_none, mock_rpc
    ):
        from shuttle.views.json_rpc import prepare_mqtt_request

        gateway = Device.objects.get(pk=self.dev_room_pi)
        device = Device.objects.get(pk=self.dev_room_47)

        mock_gateway_or_none.return_value = gateway

        created_rpc = SimpleNamespace(id=123, received=False, additional_info={})
        mock_rpc.objects.create.return_value = created_rpc

        # emulate polling hits received=True quickly
        def _filter_side_effect(id=None, received=None):
            class _QS:
                def first(self_inner):
                    if id == 123:
                        return SimpleNamespace(id=123, received=True, additional_info={"answer": "pong"})
                    return None
            return _QS()

        mock_rpc.objects.filter.side_effect = _filter_side_effect

        result = prepare_mqtt_request(device, "ping", [{"x": 1}], timeout=1.0)

        mock_connect.assert_called_once()
        mock_send.assert_called_once()
        self.assertEqual(result, {"answer": "pong"})

    @patch("shuttle.views.json_rpc.RPCMessage")
    @patch("shuttle.views.json_rpc.Relation.objects.filter")
    @patch("shuttle.views.json_rpc.Device.objects.gateway_or_none")
    @patch("shuttle.views.json_rpc.send_to_rabbitmq")
    @patch("shuttle.views.json_rpc.connect_to_rabbitmq")
    def test_prepare_mqtt_request_falls_back_to_relation_when_no_gateway(
        self, mock_connect, mock_send, mock_gateway_or_none, mock_relation_filter, mock_rpc
    ):
        from shuttle.views.json_rpc import prepare_mqtt_request

        device = Device.objects.get(pk=self.dev_room_47)
        upstream = Device.objects.get(pk=self.dev_room_pi)

        mock_gateway_or_none.return_value = None
        rel_qs = MagicMock()
        rel_qs.order_by.return_value.last.return_value = SimpleNamespace(from_id=upstream)
        mock_relation_filter.return_value = rel_qs

        created_rpc = SimpleNamespace(id=777, received=False, additional_info={})
        mock_rpc.objects.create.return_value = created_rpc

        def _filter_side_effect(id=None, received=None):
            class _QS:
                def first(self_inner):
                    if id == 777:
                        return SimpleNamespace(id=777, received=True, additional_info={"ok": True})
                    return None
            return _QS()

        mock_rpc.objects.filter.side_effect = _filter_side_effect

        res = prepare_mqtt_request(device, "status", [{}], timeout=1.0)
        self.assertEqual(res, {"ok": True})
        mock_send.assert_called_once()
        sent_message = mock_send.call_args[0][1]
        self.assertEqual(sent_message["topic"], "v1/gateway/rpc")
        self.assertEqual(sent_message["data"]["device"], device.name)

    @patch("shuttle.views.json_rpc.ControllerFile.objects.filter")
    @patch("shuttle.views.json_rpc.b_encode", return_value=b"ENC")
    @patch("shuttle.views.json_rpc.compress_data", return_value=b"COMP")
    @patch("shuttle.views.json_rpc.read_binary", return_value=b"BIN")
    @patch("shuttle.views.json_rpc.RPCMessage")
    @patch("shuttle.views.json_rpc.Device.objects.gateway_or_none")
    @patch("shuttle.views.json_rpc.send_to_rabbitmq")
    @patch("shuttle.views.json_rpc.connect_to_rabbitmq")
    def test_prepare_mqtt_request_upload_configuration_enriches_file(
        self,
        mock_connect,
        mock_send,
        mock_gateway_or_none,
        mock_rpc,
        mock_read,
        mock_comp,
        mock_benc,
        mock_cf_filter,
    ):
        from shuttle.views.json_rpc import prepare_mqtt_request

        device = Device.objects.get(pk=self.dev_room_47)
        mock_gateway_or_none.return_value = device

        fake_file = SimpleNamespace(content=SimpleNamespace(path="/tmp/media/controller/12345678901firm.bin"))
        mock_cf_filter.return_value.first.return_value = fake_file

        created_rpc = SimpleNamespace(id=999, received=False, additional_info={})
        mock_rpc.objects.create.return_value = created_rpc

        def _filter_side_effect(id=None, received=None):
            class _QS:
                def first(self_inner):
                    if id == 999:
                        return SimpleNamespace(id=999, received=True, additional_info={"done": True})
                    return None
            return _QS()

        mock_rpc.objects.filter.side_effect = _filter_side_effect

        params = [{"file": {"id": "cf-id-placeholder"}}]
        res = prepare_mqtt_request(device, "uploadConfiguration", params, timeout=1.0)
        self.assertEqual(res, {"done": True})

        sent_msg = mock_send.call_args[0][1]
        sent_params = sent_msg["data"]["data"]["params"]
        self.assertIn("name", sent_params[0]["file"])
        self.assertIn("content", sent_params[0]["file"])
        self.assertTrue(sent_params[0]["file"]["name"].endswith("firm.bin"))
        self.assertEqual(sent_params[0]["file"]["content"], "b'ENC'")

    @patch("shuttle.views.json_rpc.ControllerFile.objects.filter")
    @patch("shuttle.views.json_rpc.RPCMessage")
    @patch("shuttle.views.json_rpc.Device.objects.gateway_or_none")
    @patch("shuttle.views.json_rpc.send_to_rabbitmq")
    @patch("shuttle.views.json_rpc.connect_to_rabbitmq")
    def test_prepare_mqtt_request_upload_configuration_file_not_found(
            self, mock_connect, mock_send, mock_gateway_or_none, mock_rpc, mock_cf_filter
    ):
        from shuttle.views.json_rpc import prepare_mqtt_request

        device = Device.objects.get(pk=self.dev_room_47)
        mock_gateway_or_none.return_value = device
        mock_cf_filter.return_value.first.return_value = None

        res = prepare_mqtt_request(device, "uploadConfiguration", [{"file": {"id": "missing"}}], timeout=0.5)

        self.assertEqual(res, {"error": "Not found file."})
        mock_connect.assert_not_called()
        mock_send.assert_not_called()
        mock_rpc.objects.create.assert_called_once()

    @patch("shuttle.views.json_rpc.RPCMessage")
    @patch("shuttle.views.json_rpc.Device.objects.gateway_or_none")
    @patch("shuttle.views.json_rpc.send_to_rabbitmq")
    @patch("shuttle.views.json_rpc.connect_to_rabbitmq")
    @patch("shuttle.views.json_rpc.time.sleep", return_value=None)
    def test_prepare_mqtt_request_timeout(
        self, mock_sleep, mock_connect, mock_send, mock_gateway_or_none, mock_rpc
    ):
        from shuttle.views.json_rpc import prepare_mqtt_request

        device = Device.objects.get(pk=self.dev_room_47)
        mock_gateway_or_none.return_value = device

        created_rpc = SimpleNamespace(id=321, received=False, additional_info={})
        mock_rpc.objects.create.return_value = created_rpc

        def _filter_side_effect(id=None, received=None):
            class _QS:
                def first(self_inner):
                    return None
            return _QS()

        mock_rpc.objects.filter.side_effect = _filter_side_effect

        res = prepare_mqtt_request(device, "ping", [{}], timeout=0.9)
        self.assertEqual(res.get("device"), device.name)
        self.assertFalse(res.get("data", {}).get("success"))
        self.assertIn("Timeout", res.get("data", {}).get("msg", ""))
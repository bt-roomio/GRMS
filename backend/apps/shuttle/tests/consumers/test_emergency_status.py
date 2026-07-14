import asyncio

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from main.models import Device, RoomType


@pytest.fixture
@database_sync_to_async
def test_devices():
    device = Device.objects.get(pk="a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    device2 = Device.objects.get(pk="b2c3d4e5-f6a7-8901-bcde-f12345678901")
    return {"device": device, "device2": device2}


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestEmergencyStatusConsumer:
    async def test_connect_success(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            assert comm is not None
        finally:
            await comm.disconnect()

    async def test_connect_invalid_token(self, asgi_app):
        comm = WebsocketCommunicator(asgi_app, "/api/ws/v2/?token=invalid")
        connected, _ = await comm.connect()
        assert not connected
        await comm.disconnect()

    async def test_list_basic_telemetry(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "list",
                        "request_id": "r1",
                        "query_params": {
                            "keys": ["ip_address"],
                            "data_type": "attribute",
                            "attribute_scope": "CLIENT_SCOPE",
                            "devices": [str(test_devices["device"].id)],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "emergency_status"
            assert payload["action"] == "list"
            assert payload["request_id"] == "r1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert payload["data"] is not None
            assert isinstance(payload["data"], list)
        finally:
            await comm.disconnect()

    async def test_list_response_structure_telemetry(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "list",
                        "request_id": "r3",
                        "query_params": {
                            "keys": ["ip_address", "mac_address"],
                            "data_type": "attribute",
                            "attribute_scope": "CLIENT_SCOPE",
                            "devices": [str(test_devices["device"].id)],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, list)
            if data:
                for item in data:
                    assert "device_id" in item
                    assert "device_name" in item
                    assert "room" in item
                    assert "data" in item
                    assert isinstance(item["room"], dict)
                    assert "number" in item["room"]
                    assert "id" in item["room"]
                    assert isinstance(item["data"], list)
                    for data_item in item["data"]:
                        assert "key_name" in data_item
                        assert "ts" in data_item
                        assert "value" in data_item
        finally:
            await comm.disconnect()

    async def test_list_filter_by_devices(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "list",
                        "request_id": "r4",
                        "query_params": {
                            "keys": ["ip_address"],
                            "data_type": "attribute",
                            "attribute_scope": "CLIENT_SCOPE",
                            "devices": [str(test_devices["device"].id)],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, list)
            if data:
                for item in data:
                    assert item["device_id"] == str(test_devices["device"].id)
        finally:
            await comm.disconnect()

    async def test_list_filter_by_multiple_devices(self, ws_connect, karina_token, test_devices):
        device_ids = [str(test_devices["device"].id), str(test_devices["device2"].id)]
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "list",
                        "request_id": "r5",
                        "query_params": {
                            "keys": ["ip_address"],
                            "data_type": "attribute",
                            "attribute_scope": "CLIENT_SCOPE",
                            "devices": device_ids,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, list)
            if data:
                result_device_ids = [item["device_id"] for item in data]
                for device_id in result_device_ids:
                    assert device_id in device_ids
        finally:
            await comm.disconnect()

    async def test_list_filter_by_delisting_devices(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "list",
                        "request_id": "r6",
                        "query_params": {
                            "keys": ["ip_address"],
                            "data_type": "attribute",
                            "attribute_scope": "CLIENT_SCOPE",
                            "delisting_devices": [str(test_devices["device"].id)],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, list)
            if data:
                for item in data:
                    assert item["device_id"] != str(test_devices["device"].id)
        finally:
            await comm.disconnect()

    async def test_list_filter_by_room_types(self, ws_connect, karina_token, test_devices):
        room_type = await database_sync_to_async(RoomType.objects.first)()
        if room_type:
            comm = await ws_connect(karina_token)
            try:
                await comm.send_json_to(
                    {
                        "stream": "emergency_status",
                        "payload": {
                            "action": "list",
                            "request_id": "r7",
                            "query_params": {
                                "keys": ["ip_address"],
                                "data_type": "attribute",
                                "attribute_scope": "CLIENT_SCOPE",
                                "room_types": [room_type.title],
                            },
                        },
                    }
                )
                reply = await comm.receive_json_from()
                payload = reply.get("payload") or {}

                assert payload["response_status"] == 200
                data = payload["data"]
                assert isinstance(data, list)
                if data:
                    for item in data:
                        device = await database_sync_to_async(Device.objects.get)(id=item["device_id"])
                        if device.room and device.room.type:
                            assert device.room.type.title == room_type.title
            finally:
                await comm.disconnect()

    async def test_list_combined_filters(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "list",
                        "request_id": "r8",
                        "query_params": {
                            "keys": ["ip_address"],
                            "data_type": "attribute",
                            "attribute_scope": "CLIENT_SCOPE",
                            "devices": [str(test_devices["device"].id)],
                            "delisting_devices": [],
                            "room_types": [],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, list)
            if data:
                for item in data:
                    assert item["device_id"] == str(test_devices["device"].id)
        finally:
            await comm.disconnect()

    async def test_list_tenant_scoping(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "list",
                        "request_id": "r9",
                        "query_params": {
                            "keys": ["ip_address"],
                            "data_type": "attribute",
                            "attribute_scope": "CLIENT_SCOPE",
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, list)
            tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"
            all_device_ids = await database_sync_to_async(list)(
                Device.objects.filter(tenant_id=tenant_id).values_list("id", flat=True)
            )
            if data:
                for item in data:
                    assert item["device_id"] in [str(did) for did in all_device_ids]
        finally:
            await comm.disconnect()

    async def test_list_attribute_data_type(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "list",
                        "request_id": "r10",
                        "query_params": {
                            "keys": ["roomNumber"],
                            "data_type": "attribute",
                            "attribute_scope": "SHARED_SCOPE",
                            "devices": [str(test_devices["device"].id)],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert payload["data"] is not None
            assert isinstance(payload["data"], list)
        finally:
            await comm.disconnect()

    async def test_list_attribute_with_client_scope(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "list",
                        "request_id": "r11",
                        "query_params": {
                            "keys": ["ip_address"],
                            "data_type": "attribute",
                            "attribute_scope": "CLIENT_SCOPE",
                            "devices": [str(test_devices["device"].id)],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert isinstance(payload["data"], list)
        finally:
            await comm.disconnect()

    async def test_list_attribute_with_server_scope(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "list",
                        "request_id": "r12",
                        "query_params": {
                            "keys": ["active"],
                            "data_type": "attribute",
                            "attribute_scope": "SERVER_SCOPE",
                            "devices": [str(test_devices["device"].id)],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert isinstance(payload["data"], list)
        finally:
            await comm.disconnect()

    async def test_list_validation_missing_data_type(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "list",
                        "request_id": "r14",
                        "query_params": {
                            "keys": ["ip_address"],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 400
            assert len(payload["errors"]) > 0
        finally:
            await comm.disconnect()

    async def test_list_validation_invalid_data_type(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "list",
                        "request_id": "r15",
                        "query_params": {
                            "keys": ["ip_address"],
                            "data_type": "invalid",
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 400
            assert len(payload["errors"]) > 0
        finally:
            await comm.disconnect()

    async def test_list_validation_invalid_attribute_scope(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "list",
                        "request_id": "r16",
                        "query_params": {
                            "keys": ["ip_address"],
                            "data_type": "attribute",
                            "attribute_scope": "INVALID_SCOPE",
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 400
            assert len(payload["errors"]) > 0
        finally:
            await comm.disconnect()

    async def test_list_multiple_keys(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "list",
                        "request_id": "r17",
                        "query_params": {
                            "keys": ["ip_address", "mac_address"],
                            "data_type": "attribute",
                            "attribute_scope": "CLIENT_SCOPE",
                            "devices": [str(test_devices["device"].id)],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, list)
            if data:
                for item in data:
                    key_names = [d["key_name"] for d in item["data"]]
                    assert any(k in ["ip_address", "mac_address"] for k in key_names)
        finally:
            await comm.disconnect()

    async def test_list_empty_devices_filter(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "list",
                        "request_id": "r18",
                        "query_params": {
                            "keys": ["ip_address"],
                            "data_type": "attribute",
                            "attribute_scope": "CLIENT_SCOPE",
                            "devices": [],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert isinstance(payload["data"], list)
        finally:
            await comm.disconnect()

    async def test_list_empty_room_types_filter(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "list",
                        "request_id": "r19",
                        "query_params": {
                            "keys": ["ip_address"],
                            "data_type": "attribute",
                            "attribute_scope": "CLIENT_SCOPE",
                            "room_types": [],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert isinstance(payload["data"], list)
        finally:
            await comm.disconnect()

    async def test_subscribe_basic(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub1",
                        "query_params": {
                            "keys": ["ip_address"],
                            "data_type": "attribute",
                            "attribute_scope": "CLIENT_SCOPE",
                        },
                    },
                }
            )
            await asyncio.sleep(0.1)
        finally:
            await comm.disconnect()

    async def test_subscribe_with_filters(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "emergency_status",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub2",
                        "query_params": {
                            "keys": ["ip_address"],
                            "data_type": "attribute",
                            "attribute_scope": "CLIENT_SCOPE",
                            "devices": [str(test_devices["device"].id)],
                        },
                    },
                }
            )
            await asyncio.sleep(0.1)
        finally:
            await comm.disconnect()

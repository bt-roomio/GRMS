import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from main.models import Device
from shuttle.models import AttributeKv


@pytest.fixture
@database_sync_to_async
def test_device():
    return Device.objects.get(pk="47aef21b-6cc9-4ec5-8573-1a6f491940c0")


@pytest.fixture
@database_sync_to_async
def test_device2():
    return Device.objects.get(pk="a1561fb2-e031-42ce-812a-0ce84843c0f0")


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestInactiveDeviceAttributeConsumer:
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

    async def test_list_subscribe_basic(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "current_alarms",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls1",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "current_alarms"
            assert payload["action"] == "list_subscribe"
            assert payload["request_id"] == "ls1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert isinstance(payload["data"], list)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_response_structure(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "current_alarms",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls2",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, list)
            if data:
                item = data[0]
                assert "last_update_ts" in item
                assert "ip_address" in item
                assert "device" in item
                assert isinstance(item["device"], dict)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_with_pagination(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "current_alarms",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls3",
                        "query_params": {
                            "page": 1,
                            "size": 10,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, list)
            assert len(data) <= 10
        finally:
            await comm.disconnect()

    async def test_list_subscribe_pagination_page_2(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "current_alarms",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls4",
                        "query_params": {
                            "page": 1,
                            "size": 2,
                        },
                    },
                }
            )
            reply1 = await comm.receive_json_from()
            payload1 = reply1.get("payload") or {}
            first_page_ids = [item.get("device", {}).get("id") for item in payload1["data"]]

            await comm.send_json_to(
                {
                    "stream": "current_alarms",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls5",
                        "query_params": {
                            "page": 2,
                            "size": 2,
                        },
                    },
                }
            )
            reply2 = await comm.receive_json_from()
            payload2 = reply2.get("payload") or {}

            assert payload2["response_status"] == 200
            assert len(payload2["data"]) <= 2
            if len(payload1["data"]) > 0 and len(payload2["data"]) > 0:
                second_page_ids = [item.get("device", {}).get("id") for item in payload2["data"]]
                assert set(first_page_ids).isdisjoint(set(second_page_ids))
        finally:
            await comm.disconnect()

    async def test_list_subscribe_sort_by_last_update_ts_desc(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "current_alarms",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls6",
                        "query_params": {
                            "sort_by": "-last_update_ts",
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            results = payload["data"]
            if len(results) > 1:
                for i in range(len(results) - 1):
                    current_ts = results[i]["last_update_ts"]
                    next_ts = results[i + 1]["last_update_ts"]
                    assert current_ts >= next_ts
        finally:
            await comm.disconnect()

    async def test_list_subscribe_sort_by_last_update_ts_asc(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "current_alarms",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls7",
                        "query_params": {
                            "sort_by": "last_update_ts",
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            results = payload["data"]
            if len(results) > 1:
                for i in range(len(results) - 1):
                    current_ts = results[i]["last_update_ts"]
                    next_ts = results[i + 1]["last_update_ts"]
                    assert current_ts <= next_ts
        finally:
            await comm.disconnect()

    async def test_list_subscribe_default_sort(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "current_alarms",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls8",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            results = payload["data"]
            if len(results) > 1:
                for i in range(len(results) - 1):
                    current_ts = results[i]["last_update_ts"]
                    next_ts = results[i + 1]["last_update_ts"]
                    assert current_ts >= next_ts
        finally:
            await comm.disconnect()

    async def test_list_subscribe_default_pagination(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "current_alarms",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls9",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, list)
            assert len(data) <= 25
        finally:
            await comm.disconnect()

    async def test_list_subscribe_tenant_scoping(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "current_alarms",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls10",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"
            for item in payload["data"]:
                device_data = item.get("device", {})
                if device_data.get("tenant"):
                    assert str(device_data["tenant"]) == tenant_id
        finally:
            await comm.disconnect()

    async def test_list_subscribe_only_inactive_devices(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "current_alarms",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls11",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            active_attr = await database_sync_to_async(
                lambda: AttributeKv.objects.filter(
                    attribute_type=AttributeKv.SERVER_SCOPE,
                    attribute_key="active",
                    bool_v=True,
                ).values_list("entity_id", flat=True)
            )()
            result_device_ids = [
                item.get("device", {}).get("id") for item in payload["data"] if item.get("device", {}).get("id")
            ]
            for device_id in result_device_ids:
                assert device_id not in active_attr
        finally:
            await comm.disconnect()

    async def test_list_subscribe_only_devices_in_spaces(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "current_alarms",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls12",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            for item in payload["data"]:
                device_data = item.get("device", {})
                device_id = device_data.get("id")
                if device_id:
                    device = await database_sync_to_async(Device.objects.get)(id=device_id)
                    has_room = device.room is not None
                    has_public_space = await database_sync_to_async(lambda: device.device_public_spaces.exists())()
                    assert has_room or has_public_space
        finally:
            await comm.disconnect()

    async def test_list_subscribe_validation_invalid_sort(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "current_alarms",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls13",
                        "query_params": {
                            "sort_by": "invalid_field",
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

    async def test_list_subscribe_validation_invalid_page(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "current_alarms",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls14",
                        "query_params": {
                            "page": 0,
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

    async def test_list_subscribe_validation_invalid_size(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "current_alarms",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls15",
                        "query_params": {
                            "size": 501,
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

    async def test_list_subscribe_empty_result(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            other_tenant_device = await database_sync_to_async(
                lambda: Device.objects.exclude(tenant_id="28c81921-f78e-4864-87d2-cec674f19d1c").first()
            )()
            if other_tenant_device:
                await comm.send_json_to(
                    {
                        "stream": "current_alarms",
                        "payload": {
                            "action": "list_subscribe",
                            "request_id": "ls16",
                            "query_params": {},
                        },
                    }
                )
                reply = await comm.receive_json_from()
                payload = reply.get("payload") or {}

                assert payload["response_status"] == 200
                assert isinstance(payload["data"], list)
                for item in payload["data"]:
                    device_data = item.get("device", {})
                    if device_data.get("tenant"):
                        assert str(device_data["tenant"]) == "28c81921-f78e-4864-87d2-cec674f19d1c"
        finally:
            await comm.disconnect()

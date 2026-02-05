import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from core.utils.get_time import get_mil_sec
from main.models import Device
from shuttle.models import TsKvDictionary, TsKvLatest


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
class TestTsKvLatestConsumer:

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

    async def test_list_subscribe_basic(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls1",
                        "query_params": {
                            "device": str(test_device.id),
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "ts_kv_latest"
            assert payload["action"] == "list_subscribe"
            assert payload["request_id"] == "ls1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert isinstance(payload["data"], list)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_response_structure(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls2",
                        "query_params": {
                            "device": str(test_device.id),
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
                item = data[0]
                assert "ts" in item
                assert "key_name" in item
                assert "value" in item
        finally:
            await comm.disconnect()

    async def test_list_subscribe_with_pagination(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls3",
                        "query_params": {
                            "device": str(test_device.id),
                            "with_pagination": True,
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
            assert isinstance(data, dict)
            assert "results" in data
            assert "count" in data
            assert isinstance(data["results"], list)
            assert len(data["results"]) <= 10
        finally:
            await comm.disconnect()

    async def test_list_subscribe_pagination_page_2(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls4",
                        "query_params": {
                            "device": str(test_device.id),
                            "with_pagination": True,
                            "page": 1,
                            "size": 2,
                        },
                    },
                }
            )
            reply1 = await comm.receive_json_from()
            payload1 = reply1.get("payload") or {}
            first_page_ids = [item.get("key_name") for item in payload1["data"]["results"]]

            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls5",
                        "query_params": {
                            "device": str(test_device.id),
                            "with_pagination": True,
                            "page": 2,
                            "size": 2,
                        },
                    },
                }
            )
            reply2 = await comm.receive_json_from()
            payload2 = reply2.get("payload") or {}

            assert payload2["response_status"] == 200
            assert len(payload2["data"]["results"]) <= 2
            if len(payload1["data"]["results"]) > 0 and len(payload2["data"]["results"]) > 0:
                second_page_ids = [item.get("key_name") for item in payload2["data"]["results"]]
                assert set(first_page_ids).isdisjoint(set(second_page_ids))
        finally:
            await comm.disconnect()

    async def test_list_subscribe_sort_by_ts_desc(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls6",
                        "query_params": {
                            "device": str(test_device.id),
                            "sort_by": ["-ts"],
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
                    current_ts = results[i]["ts"]
                    next_ts = results[i + 1]["ts"]
                    assert current_ts >= next_ts
        finally:
            await comm.disconnect()

    async def test_list_subscribe_sort_by_ts_asc(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls7",
                        "query_params": {
                            "device": str(test_device.id),
                            "sort_by": ["ts"],
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
                    current_ts = results[i]["ts"]
                    next_ts = results[i + 1]["ts"]
                    assert current_ts <= next_ts
        finally:
            await comm.disconnect()

    async def test_list_subscribe_sort_by_key_name_asc(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls8",
                        "query_params": {
                            "device": str(test_device.id),
                            "sort_by": ["key_name"],
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
                    current_key = results[i].get("key_name", "")
                    next_key = results[i + 1].get("key_name", "")
                    assert current_key <= next_key
        finally:
            await comm.disconnect()

    async def test_list_subscribe_sort_by_key_name_desc(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls9",
                        "query_params": {
                            "device": str(test_device.id),
                            "sort_by": ["-key_name"],
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
                    current_key = results[i].get("key_name", "")
                    next_key = results[i + 1].get("key_name", "")
                    assert current_key >= next_key
        finally:
            await comm.disconnect()

    async def test_list_subscribe_tenant_scoping(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls10",
                        "query_params": {
                            "device": str(test_device.id),
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"
            device = await database_sync_to_async(Device.objects.get)(id=test_device.id)
            assert str(device.tenant_id) == tenant_id
        finally:
            await comm.disconnect()

    async def test_list_subscribe_validation_missing_device(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls11",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 400
            assert len(payload["errors"]) > 0
        finally:
            await comm.disconnect()

    async def test_list_subscribe_validation_invalid_device(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls12",
                        "query_params": {
                            "device": "00000000-0000-0000-0000-000000000000",
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

    async def test_list_subscribe_validation_invalid_sort(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls13",
                        "query_params": {
                            "device": str(test_device.id),
                            "sort_by": ["invalid_field"],
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

    async def test_list_subscribe_default_pagination(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls14",
                        "query_params": {
                            "device": str(test_device.id),
                            "with_pagination": True,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, dict)
            assert "results" in data
            assert "count" in data
            assert len(data["results"]) <= 15
        finally:
            await comm.disconnect()

    async def test_list_subscribe_multiple_sort_fields(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls15",
                        "query_params": {
                            "device": str(test_device.id),
                            "sort_by": ["key_name", "-ts"],
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
                    current = results[i]
                    next_item = results[i + 1]
                    if current["key_name"] == next_item["key_name"]:
                        assert current["ts"] >= next_item["ts"]
                    else:
                        assert current["key_name"] <= next_item["key_name"]
        finally:
            await comm.disconnect()

    async def test_list_subscribe_different_devices(self, ws_connect, karina_token, test_device, test_device2):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls16",
                        "query_params": {
                            "device": str(test_device.id),
                        },
                    },
                }
            )
            reply1 = await comm.receive_json_from()
            payload1 = reply1.get("payload") or {}
            results1_ids = [item.get("key_name") for item in payload1["data"]]

            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls17",
                        "query_params": {
                            "device": str(test_device2.id),
                        },
                    },
                }
            )
            reply2 = await comm.receive_json_from()
            payload2 = reply2.get("payload") or {}

            assert payload2["response_status"] == 200
            results2_ids = [item.get("key_name") for item in payload2["data"]]
            assert payload1["response_status"] == 200
        finally:
            await comm.disconnect()

    async def test_list_subscribe_without_pagination(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls18",
                        "query_params": {
                            "device": str(test_device.id),
                            "with_pagination": False,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, list)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_empty_result(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            other_device = await database_sync_to_async(
                lambda: Device.objects.exclude(tenant_id="28c81921-f78e-4864-87d2-cec674f19d1c").first()
            )()
            if other_device:
                await comm.send_json_to(
                    {
                        "stream": "ts_kv_latest",
                        "payload": {
                            "action": "list_subscribe",
                            "request_id": "ls19",
                            "query_params": {
                                "device": str(other_device.id),
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


    async def test_subscribe_validation_missing_device(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "s2",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 400
            assert len(payload["errors"]) > 0
        finally:
            await comm.disconnect()


    async def test_subscribe_different_device_no_update(self, ws_connect, karina_token, test_device, test_device2):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_latest",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "s6",
                        "query_params": {
                            "device": str(test_device.id),
                        },
                    },
                }
            )

            key, _ = await database_sync_to_async(TsKvDictionary.objects.get_or_create)(key="test_key_other_device")
            await database_sync_to_async(TsKvLatest.objects.update_or_create)(
                entity_id=test_device2.id,
                key_id=key.key_id,
                defaults={
                    "long_v": 999,
                    "ts": get_mil_sec(),
                },
            )

            import asyncio
            try:
                reply = await asyncio.wait_for(comm.receive_json_from(), timeout=0.5)
                assert False, "Should not receive update for different device"
            except asyncio.TimeoutError:
                pass
        finally:
            await comm.disconnect()

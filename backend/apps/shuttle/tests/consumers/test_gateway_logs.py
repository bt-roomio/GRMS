import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from main.models import Device
from shuttle.models import TsKv, TsKvDictionary


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
class TestGatewayLogsConsumer:

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

    async def test_list_basic(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            end_ts = datetime.now(timezone.utc).isoformat()
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l1",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "humidity",
                            "start_ts": start_ts,
                            "end_ts": end_ts,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "gateway_logs"
            assert payload["action"] == "list"
            assert payload["request_id"] == "l1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert "results" in payload["data"]
            assert "count" in payload["data"]
            assert isinstance(payload["data"]["results"], list)
        finally:
            await comm.disconnect()

    async def test_list_response_structure(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            end_ts = datetime.now(timezone.utc).isoformat()
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l2",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "temperature",
                            "start_ts": start_ts,
                            "end_ts": end_ts,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert "results" in data
            assert "count" in data
            assert isinstance(data["results"], list)
            if data["results"]:
                item = data["results"][0]
                assert "ts" in item
                assert "key_name" in item
                assert "value" in item
                assert item["key_name"] == "temperature"
        finally:
            await comm.disconnect()

    async def test_list_with_pagination(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            end_ts = datetime.now(timezone.utc).isoformat()
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l3",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "humidity",
                            "start_ts": start_ts,
                            "end_ts": end_ts,
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
            assert len(data["results"]) <= 10
        finally:
            await comm.disconnect()

    async def test_list_pagination_page_2(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            end_ts = datetime.now(timezone.utc).isoformat()
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l4",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "humidity",
                            "start_ts": start_ts,
                            "end_ts": end_ts,
                            "page": 1,
                            "size": 2,
                        },
                    },
                }
            )
            reply1 = await comm.receive_json_from()
            payload1 = reply1.get("payload") or {}
            first_page_ts = [item.get("ts") for item in payload1["data"]["results"]]

            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l5",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "humidity",
                            "start_ts": start_ts,
                            "end_ts": end_ts,
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
                second_page_ts = [item.get("ts") for item in payload2["data"]["results"]]
                assert set(first_page_ts).isdisjoint(set(second_page_ts))
        finally:
            await comm.disconnect()

    async def test_list_sort_by_ts_desc(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            end_ts = datetime.now(timezone.utc).isoformat()
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l6",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "humidity",
                            "start_ts": start_ts,
                            "end_ts": end_ts,
                            "sort_by": ["-ts"],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            results = payload["data"]["results"]
            if len(results) > 1:
                for i in range(len(results) - 1):
                    current_ts = datetime.fromisoformat(results[i]["ts"].replace("Z", "+00:00"))
                    next_ts = datetime.fromisoformat(results[i + 1]["ts"].replace("Z", "+00:00"))
                    assert current_ts >= next_ts
        finally:
            await comm.disconnect()

    async def test_list_sort_by_ts_asc(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            end_ts = datetime.now(timezone.utc).isoformat()
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l7",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "humidity",
                            "start_ts": start_ts,
                            "end_ts": end_ts,
                            "sort_by": ["ts"],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            results = payload["data"]["results"]
            if len(results) > 1:
                for i in range(len(results) - 1):
                    current_ts = datetime.fromisoformat(results[i]["ts"].replace("Z", "+00:00"))
                    next_ts = datetime.fromisoformat(results[i + 1]["ts"].replace("Z", "+00:00"))
                    assert current_ts <= next_ts
        finally:
            await comm.disconnect()

    async def test_list_with_date_range(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            end_ts = datetime.now(timezone.utc)
            start_ts = end_ts - timedelta(days=1)
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l8",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "humidity",
                            "start_ts": start_ts.isoformat(),
                            "end_ts": end_ts.isoformat(),
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            results = payload["data"]["results"]
            for item in results:
                item_ts = datetime.fromisoformat(item["ts"].replace("Z", "+00:00"))
                assert start_ts <= item_ts <= end_ts
        finally:
            await comm.disconnect()

    async def test_list_without_end_ts(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l9",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "humidity",
                            "start_ts": start_ts,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert "results" in payload["data"]
        finally:
            await comm.disconnect()

    async def test_list_default_pagination(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            end_ts = datetime.now(timezone.utc).isoformat()
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l10",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "humidity",
                            "start_ts": start_ts,
                            "end_ts": end_ts,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert len(data["results"]) <= 15
        finally:
            await comm.disconnect()

    async def test_list_tenant_scoping(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            end_ts = datetime.now(timezone.utc).isoformat()
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l11",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "humidity",
                            "start_ts": start_ts,
                            "end_ts": end_ts,
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

    async def test_list_different_devices(self, ws_connect, karina_token, test_device, test_device2):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            end_ts = datetime.now(timezone.utc).isoformat()
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l12",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "humidity",
                            "start_ts": start_ts,
                            "end_ts": end_ts,
                        },
                    },
                }
            )
            reply1 = await comm.receive_json_from()
            payload1 = reply1.get("payload") or {}

            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l13",
                        "query_params": {
                            "device": str(test_device2.id),
                            "key": "humidity",
                            "start_ts": start_ts,
                            "end_ts": end_ts,
                        },
                    },
                }
            )
            reply2 = await comm.receive_json_from()
            payload2 = reply2.get("payload") or {}

            assert payload1["response_status"] == 200
            assert payload2["response_status"] == 200
        finally:
            await comm.disconnect()

    async def test_list_different_keys(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            end_ts = datetime.now(timezone.utc).isoformat()
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l14",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "humidity",
                            "start_ts": start_ts,
                            "end_ts": end_ts,
                        },
                    },
                }
            )
            reply1 = await comm.receive_json_from()
            payload1 = reply1.get("payload") or {}

            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l15",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "temperature",
                            "start_ts": start_ts,
                            "end_ts": end_ts,
                        },
                    },
                }
            )
            reply2 = await comm.receive_json_from()
            payload2 = reply2.get("payload") or {}

            assert payload1["response_status"] == 200
            assert payload2["response_status"] == 200
            if payload1["data"]["results"]:
                assert all(item["key_name"] == "humidity" for item in payload1["data"]["results"])
            if payload2["data"]["results"]:
                assert all(item["key_name"] == "temperature" for item in payload2["data"]["results"])
        finally:
            await comm.disconnect()

    async def test_list_validation_missing_device(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l16",
                        "query_params": {
                            "key": "humidity",
                            "start_ts": start_ts,
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

    async def test_list_validation_missing_key(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l17",
                        "query_params": {
                            "device": str(test_device.id),
                            "start_ts": start_ts,
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

    async def test_list_validation_missing_start_ts(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l18",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "humidity",
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

    async def test_list_validation_invalid_device(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l19",
                        "query_params": {
                            "device": "00000000-0000-0000-0000-000000000000",
                            "key": "humidity",
                            "start_ts": start_ts,
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

    async def test_list_validation_invalid_sort(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            end_ts = datetime.now(timezone.utc).isoformat()
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l20",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "humidity",
                            "start_ts": start_ts,
                            "end_ts": end_ts,
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

    async def test_list_validation_invalid_page(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            end_ts = datetime.now(timezone.utc).isoformat()
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l21",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "humidity",
                            "start_ts": start_ts,
                            "end_ts": end_ts,
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

    async def test_list_validation_invalid_size(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            end_ts = datetime.now(timezone.utc).isoformat()
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "list",
                        "request_id": "l22",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "humidity",
                            "start_ts": start_ts,
                            "end_ts": end_ts,
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

    async def test_subscribe_basic(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            key, _ = await database_sync_to_async(TsKvDictionary.objects.get_or_create)(key="test_gateway_key")
            await comm.send_json_to(
                {
                    "stream": "gateway_logs",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "s1",
                        "query_params": {
                            "device": str(test_device.id),
                            "key": "test_gateway_key",
                            "start_ts": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                        },
                    },
                }
            )
            await asyncio.sleep(1)
            await database_sync_to_async(TsKv.objects.create)(
                entity_id=test_device.id,
                key_id=key.key_id,
                str_v="test_value",
                ts=datetime.now(timezone.utc),
            )
            reply = await asyncio.wait_for(comm.receive_json_from(), timeout=2.0)
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "gateway_logs"
            assert payload["action"] == "subscribe"
            assert payload["request_id"] == "s1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert payload["data"]
            assert isinstance(payload["data"], dict)
            assert "key_name" in payload["data"]
            assert "ts" in payload["data"]
            assert "value" in payload["data"]
            assert payload["data"]["key_name"] == "test_gateway_key"
            assert payload["data"]["value"] == "test_value"
        finally:
            await comm.disconnect()


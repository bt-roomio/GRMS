import pytest
from datetime import datetime, timedelta, timezone
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from main.models import Device


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
class TestTagLogsConsumer:

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
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls1",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity", "temperature"],
                            "start_ts": start_ts,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "tag_logs"
            assert payload["action"] == "list_subscribe"
            assert payload["request_id"] == "ls1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert payload["data"]
            assert "results" in payload["data"]
            assert "count" in payload["data"]
            assert isinstance(payload["data"]["results"], list)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_response_structure(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls2",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity"],
                            "start_ts": start_ts,
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
        finally:
            await comm.disconnect()

    async def test_list_subscribe_with_end_ts(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            end_ts = datetime.now(timezone.utc)
            start_ts = (end_ts - timedelta(days=1)).isoformat()
            end_ts_str = end_ts.isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls3",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity", "temperature"],
                            "start_ts": start_ts,
                            "end_ts": end_ts_str,
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
        finally:
            await comm.disconnect()

    async def test_list_subscribe_all_tags(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls4",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity"],
                            "all_tags": True,
                            "start_ts": start_ts,
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
        finally:
            await comm.disconnect()

    async def test_list_subscribe_sort_by_ts_desc(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls5",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity", "temperature"],
                            "start_ts": start_ts,
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
                    current_ts = results[i]["ts"]
                    next_ts = results[i + 1]["ts"]
                    assert current_ts >= next_ts
        finally:
            await comm.disconnect()

    async def test_list_subscribe_sort_by_ts_asc(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls6",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity", "temperature"],
                            "start_ts": start_ts,
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
                    current_ts = results[i]["ts"]
                    next_ts = results[i + 1]["ts"]
                    assert current_ts <= next_ts
        finally:
            await comm.disconnect()

    async def test_list_subscribe_pagination(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls7",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity", "temperature"],
                            "start_ts": start_ts,
                            "page": 1,
                            "size": 5,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert len(payload["data"]["results"]) <= 5
            assert payload["data"]["count"] >= len(payload["data"]["results"])
        finally:
            await comm.disconnect()

    async def test_list_subscribe_pagination_page_2(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls8",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity", "temperature"],
                            "start_ts": start_ts,
                            "page": 1,
                            "size": 2,
                        },
                    },
                }
            )
            reply1 = await comm.receive_json_from()
            payload1 = reply1.get("payload") or {}
            first_page_count = len(payload1["data"]["results"])

            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls9",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity", "temperature"],
                            "start_ts": start_ts,
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
            if first_page_count > 0 and len(payload2["data"]["results"]) > 0:
                first_page_ts = [item["ts"] for item in payload1["data"]["results"]]
                second_page_ts = [item["ts"] for item in payload2["data"]["results"]]
                assert set(first_page_ts).isdisjoint(set(second_page_ts))
        finally:
            await comm.disconnect()

    async def test_list_subscribe_tenant_scoping(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls10",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity", "temperature"],
                            "start_ts": start_ts,
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
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls11",
                        "query_params": {
                            "keys": ["humidity"],
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

    async def test_list_subscribe_validation_missing_keys(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls12",
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

    async def test_list_subscribe_validation_missing_start_ts(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls13",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity"],
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

    async def test_list_subscribe_validation_invalid_device(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls14",
                        "query_params": {
                            "device": "00000000-0000-0000-0000-000000000000",
                            "keys": ["humidity"],
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

    async def test_list_subscribe_validation_invalid_sort(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls15",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity"],
                            "start_ts": start_ts,
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

    async def test_list_subscribe_validation_invalid_page(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls16",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity"],
                            "start_ts": start_ts,
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

    async def test_list_subscribe_validation_invalid_size(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls17",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity"],
                            "start_ts": start_ts,
                            "size": 600,
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

    async def test_list_subscribe_multiple_keys(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls18",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity", "temperature", "cpuUsage", "memoryUsage"],
                            "start_ts": start_ts,
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
        finally:
            await comm.disconnect()

    async def test_list_subscribe_combined_filters(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            end_ts = datetime.now(timezone.utc)
            start_ts = (end_ts - timedelta(days=1)).isoformat()
            end_ts_str = end_ts.isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls19",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity", "temperature"],
                            "start_ts": start_ts,
                            "end_ts": end_ts_str,
                            "sort_by": ["-ts"],
                            "page": 1,
                            "size": 10,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            results = payload["data"]["results"]
            assert len(results) <= 10
            if len(results) > 1:
                for i in range(len(results) - 1):
                    assert results[i]["ts"] >= results[i + 1]["ts"]
        finally:
            await comm.disconnect()

    async def test_list_subscribe_default_sort(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls21",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity", "temperature"],
                            "start_ts": start_ts,
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
                    current_ts = results[i]["ts"]
                    next_ts = results[i + 1]["ts"]
                    assert current_ts >= next_ts
        finally:
            await comm.disconnect()

    async def test_list_subscribe_default_pagination(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await comm.send_json_to(
                {
                    "stream": "tag_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls22",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity", "temperature"],
                            "start_ts": start_ts,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert len(payload["data"]["results"]) <= 15
            assert payload["data"]["count"] >= len(payload["data"]["results"])
        finally:
            await comm.disconnect()

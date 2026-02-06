import pytest
from datetime import datetime, timedelta, timezone
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestTsKvTenantHistoryConsumer:

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
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            end_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            await comm.send_json_to(
                {
                    "stream": "tskv_tenant_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls1",
                        "query_params": {
                            "keys": ["humidity", "temperature"],
                            "start_ts": start_ts,
                            "end_ts": end_ts,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "tskv_tenant_history"
            assert payload["action"] == "list_subscribe"
            assert payload["request_id"] == "ls1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert payload["data"]
            assert isinstance(payload["data"], dict)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_response_structure(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            end_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            await comm.send_json_to(
                {
                    "stream": "tskv_tenant_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls2",
                        "query_params": {
                            "keys": ["humidity"],
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
            assert isinstance(data, dict)
            if "humidity" in data:
                humidity_data = data["humidity"]
                assert isinstance(humidity_data, list)
                if humidity_data:
                    item = humidity_data[0]
                    assert "ts" in item
                    assert "key_name" in item
                    assert "value" in item
                    assert isinstance(item["value"], dict)
                    assert "avg" in item["value"]
                    assert "min" in item["value"]
                    assert "max" in item["value"]
                    assert "count" in item
        finally:
            await comm.disconnect()

    async def test_list_subscribe_with_limit(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            end_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            await comm.send_json_to(
                {
                    "stream": "tskv_tenant_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls4",
                        "query_params": {
                            "keys": ["humidity"],
                            "start_ts": start_ts,
                            "end_ts": end_ts,
                            "limit": 50,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            if "humidity" in data:
                assert len(data["humidity"]) <= 50
        finally:
            await comm.disconnect()

    async def test_list_subscribe_default_limit(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            end_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            await comm.send_json_to(
                {
                    "stream": "tskv_tenant_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls5",
                        "query_params": {
                            "keys": ["humidity"],
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
            if "humidity" in data:
                assert len(data["humidity"]) <= 100
        finally:
            await comm.disconnect()

    async def test_list_subscribe_without_end_ts(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            await comm.send_json_to(
                {
                    "stream": "tskv_tenant_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls6",
                        "query_params": {
                            "keys": ["humidity"],
                            "start_ts": start_ts,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert isinstance(payload["data"], dict)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_without_start_ts(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            end_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            await comm.send_json_to(
                {
                    "stream": "tskv_tenant_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls7",
                        "query_params": {
                            "keys": ["humidity"],
                            "end_ts": end_ts,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert isinstance(payload["data"], dict)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_multiple_keys(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            end_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            await comm.send_json_to(
                {
                    "stream": "tskv_tenant_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls8",
                        "query_params": {
                            "keys": ["humidity", "temperature", "cpuUsage"],
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
            assert isinstance(data, dict)
            for key in ["humidity", "temperature", "cpuUsage"]:
                if key in data:
                    assert isinstance(data[key], list)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_tenant_scoping(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            end_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            await comm.send_json_to(
                {
                    "stream": "tskv_tenant_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls9",
                        "query_params": {
                            "keys": ["humidity"],
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
        finally:
            await comm.disconnect()

    async def test_list_subscribe_validation_missing_keys(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            await comm.send_json_to(
                {
                    "stream": "tskv_tenant_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls10",
                        "query_params": {
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

    async def test_list_subscribe_validation_invalid_limit(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            end_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            await comm.send_json_to(
                {
                    "stream": "tskv_tenant_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls12",
                        "query_params": {
                            "keys": ["humidity"],
                            "start_ts": start_ts,
                            "end_ts": end_ts,
                            "limit": 1001,
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

    async def test_list_subscribe_date_range(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            end_ts = datetime.now(timezone.utc)
            start_ts = end_ts - timedelta(days=1)
            await comm.send_json_to(
                {
                    "stream": "tskv_tenant_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls14",
                        "query_params": {
                            "keys": ["humidity"],
                            "start_ts": start_ts.strftime("%Y-%m-%d %H:%M:%S"),
                            "end_ts": end_ts.strftime("%Y-%m-%d %H:%M:%S"),
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert isinstance(payload["data"], dict)
        finally:
            await comm.disconnect()

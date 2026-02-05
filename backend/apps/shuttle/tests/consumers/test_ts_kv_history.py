import pytest
from datetime import datetime, timedelta, timezone
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from main.models import Device, Room


def _start_ts() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")


def _base_query_params(*, device_id: str, keys: list[str], **overrides) -> dict:
    return {
        "device": device_id,
        "start_ts": _start_ts(),
        "interval": "1 day",
        "limit": 5,
        "auto_fill": False,
        "agg": "Max",
        "keys": keys,
        "sort_by": ["interval_ts"],
        **overrides,
    }


@pytest.fixture
@database_sync_to_async
def test_device():
    return Device.objects.get(pk="47aef21b-6cc9-4ec5-8573-1a6f491940c0")


@pytest.fixture
@database_sync_to_async
def test_room():
    return Room.objects.get(pk="df77f910-2dcd-45cf-b6be-054c744561a7")


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestTsKvHistoryConsumer:

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
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls1",
                        "query_params": {
                            **_base_query_params(
                                device_id=str(test_device.id),
                                keys=["humidity", "temperature"],
                            )
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "ts_kv_history"
            assert payload["action"] == "list_subscribe"
            assert payload["request_id"] == "ls1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert payload["data"]
            assert isinstance(payload["data"], dict)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_response_structure(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls2",
                        "query_params": {
                            **_base_query_params(
                                device_id=str(test_device.id),
                                keys=["humidity"],
                            )
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
                assert isinstance(data["humidity"], list)
                if data["humidity"]:
                    item = data["humidity"][0]
                    assert "ts" in item
                    assert "key_name" in item
                    assert "value" in item
        finally:
            await comm.disconnect()

    async def test_list_subscribe_with_start_ts(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls3",
                        "query_params": {
                            **_base_query_params(
                                device_id=str(test_device.id),
                                keys=["humidity", "temperature"],
                                start_ts=start_ts,
                            )
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, dict)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_with_interval(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls4",
                        "query_params": {
                            **_base_query_params(
                                device_id=str(test_device.id),
                                keys=["humidity", "temperature"],
                                interval="1 hour",
                            )
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, dict)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_with_agg(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls5",
                        "query_params": {
                            **_base_query_params(
                                device_id=str(test_device.id),
                                keys=["humidity", "temperature"],
                                agg="Min",
                            )
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, dict)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_with_limit(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls6",
                        "query_params": {
                            **_base_query_params(
                                device_id=str(test_device.id),
                                keys=["humidity", "temperature"],
                                limit=50,
                            )
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, dict)
            for _, values in data.items():
                assert len(values) <= 50
        finally:
            await comm.disconnect()

    async def test_list_subscribe_default_limit(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls7",
                        "query_params": {
                            **_base_query_params(
                                device_id=str(test_device.id),
                                keys=["humidity", "temperature"],
                            )
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, dict)
            for _, values in data.items():
                assert len(values) <= 100
        finally:
            await comm.disconnect()

    async def test_list_subscribe_with_room(self, ws_connect, karina_token, test_room):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls8",
                        "query_params": {
                            **_base_query_params(
                                device_id="47aef21b-6cc9-4ec5-8573-1a6f491940c0",
                                keys=["humidity", "temperature"],
                                room=str(test_room.id),
                            )
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, dict)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_with_sort_by(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls9",
                        "query_params": {
                            **_base_query_params(
                                device_id=str(test_device.id),
                                keys=["humidity", "temperature"],
                                sort_by=["-interval_ts"],
                            )
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, dict)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_with_auto_fill(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls10",
                        "query_params": {
                            **_base_query_params(
                                device_id=str(test_device.id),
                                keys=["humidity", "temperature"],
                                auto_fill=False,
                            )
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, dict)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_validation_missing_device(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            start_ts = _start_ts()
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls11",
                        "query_params": {
                            "keys": ["humidity"],
                            "start_ts": start_ts,
                            "interval": "1 day",
                            "limit": 5,
                            "auto_fill": False,
                            "agg": "Max",
                            "sort_by": ["interval_ts"],
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
            start_ts = _start_ts()
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls12",
                        "query_params": {
                            "device": str(test_device.id),
                            "start_ts": start_ts,
                            "interval": "1 day",
                            "limit": 5,
                            "auto_fill": False,
                            "agg": "Max",
                            "sort_by": ["interval_ts"],
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
            start_ts = _start_ts()
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls13",
                        "query_params": {
                            "device": "00000000-0000-0000-0000-000000000000",
                            "keys": ["humidity"],
                            "start_ts": start_ts,
                            "interval": "1 day",
                            "limit": 5,
                            "auto_fill": False,
                            "agg": "Max",
                            "sort_by": ["interval_ts"],
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

    async def test_list_subscribe_validation_invalid_agg(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = _start_ts()
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls14",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity"],
                            "start_ts": start_ts,
                            "agg": "InvalidAgg",
                            "interval": "1 day",
                            "limit": 5,
                            "auto_fill": False,
                            "sort_by": ["interval_ts"],
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

    async def test_list_subscribe_validation_invalid_limit(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            start_ts = _start_ts()
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls15",
                        "query_params": {
                            "device": str(test_device.id),
                            "keys": ["humidity"],
                            "start_ts": start_ts,
                            "limit": 2000,
                            "interval": "1 day",
                            "auto_fill": False,
                            "agg": "Max",
                            "sort_by": ["interval_ts"],
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
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls16",
                        "query_params": {
                            **_base_query_params(
                                device_id=str(test_device.id),
                                keys=["humidity", "temperature", "cpuUsage", "memoryUsage"],
                            )
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, dict)
        finally:
            await comm.disconnect()


    async def test_list_subscribe_different_agg_functions(self, ws_connect, karina_token, test_device):
        agg_functions = ["Min", "Max", "Avg", "Sum", "Count"]
        for agg in agg_functions:
            comm = await ws_connect(karina_token)
            try:
                await comm.send_json_to(
                    {
                        "stream": "ts_kv_history",
                        "payload": {
                            "action": "list_subscribe",
                            "request_id": f"ls18_{agg}",
                            "query_params": {
                                **_base_query_params(
                                    device_id=str(test_device.id),
                                    keys=["humidity"],
                                    agg=agg,
                                )
                            },
                        },
                    }
                )
                reply = await comm.receive_json_from()
                payload = reply.get("payload") or {}

                assert payload["response_status"] == 200
                data = payload["data"]
                assert isinstance(data, dict)
            finally:
                await comm.disconnect()

    async def test_list_subscribe_different_intervals(self, ws_connect, karina_token, test_device):
        intervals = ["1 hour", "1 day", "1 week", "month", "year"]
        for interval in intervals:
            comm = await ws_connect(karina_token)
            try:
                await comm.send_json_to(
                    {
                        "stream": "ts_kv_history",
                        "payload": {
                            "action": "list_subscribe",
                            "request_id": f"ls19_{interval}",
                            "query_params": {
                                **_base_query_params(
                                    device_id=str(test_device.id),
                                    keys=["humidity"],
                                    interval=interval,
                                )
                            },
                        },
                    }
                )
                reply = await comm.receive_json_from()
                payload = reply.get("payload") or {}

                assert payload["response_status"] == 200
                data = payload["data"]
                assert isinstance(data, dict)
            finally:
                await comm.disconnect()

    async def test_list_subscribe_default_agg(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls20",
                        "query_params": {
                            **_base_query_params(
                                device_id=str(test_device.id),
                                keys=["humidity", "temperature"],
                            )
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, dict)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_default_auto_fill(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls21",
                        "query_params": {
                            **_base_query_params(
                                device_id=str(test_device.id),
                                keys=["humidity", "temperature"],
                            )
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, dict)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_single_key(self, ws_connect, karina_token, test_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "ts_kv_history",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls22",
                        "query_params": {
                            **_base_query_params(
                                device_id=str(test_device.id),
                                keys=["temperature"],
                            )
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data, dict)
        finally:
            await comm.disconnect()

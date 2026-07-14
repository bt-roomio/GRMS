import pytest
from channels.testing import WebsocketCommunicator


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestNeedSyncConsumer:
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
                    "stream": "need_sync",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls1",
                        "query_params": {
                            "page": 1,
                            "size": 50,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "need_sync"
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

    async def test_list_subscribe_empty_result(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "need_sync",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls2",
                        "query_params": {
                            "page": 1,
                            "size": 50,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert isinstance(payload["data"]["results"], list)
            assert isinstance(payload["data"]["count"], int)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_default_sort(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "need_sync",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls3",
                        "query_params": {
                            "page": 1,
                            "size": 50,
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
                    current_ts = results[i]["created_at"]
                    next_ts = results[i + 1]["created_at"]
                    assert current_ts >= next_ts
        finally:
            await comm.disconnect()

    async def test_list_subscribe_sort_by_created_at_desc(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "need_sync",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls4",
                        "query_params": {
                            "sort_by": ["-created_at"],
                            "page": 1,
                            "size": 50,
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
                    current_ts = results[i]["created_at"]
                    next_ts = results[i + 1]["created_at"]
                    assert current_ts >= next_ts
        finally:
            await comm.disconnect()

    async def test_list_subscribe_sort_by_created_at_asc(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "need_sync",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls5",
                        "query_params": {
                            "sort_by": ["created_at"],
                            "page": 1,
                            "size": 50,
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
                    current_ts = results[i]["created_at"]
                    next_ts = results[i + 1]["created_at"]
                    assert current_ts <= next_ts
        finally:
            await comm.disconnect()

    async def test_list_subscribe_pagination(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "need_sync",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls6",
                        "query_params": {
                            "page": 1,
                            "size": 2,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert len(payload["data"]["results"]) <= 2
            assert payload["data"]["count"] >= len(payload["data"]["results"])
        finally:
            await comm.disconnect()

    async def test_list_subscribe_pagination_page_2(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "need_sync",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls7",
                        "query_params": {
                            "page": 1,
                            "size": 2,
                        },
                    },
                }
            )
            reply1 = await comm.receive_json_from()
            payload1 = reply1.get("payload") or {}
            assert payload1["response_status"] == 200
            assert payload1["data"] is not None
            first_page_created_ats = [item["created_at"] for item in payload1["data"]["results"]]

            await comm.send_json_to(
                {
                    "stream": "need_sync",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls8",
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
            assert len(payload2["data"]["results"]) <= 2
            if len(payload1["data"]["results"]) > 0 and len(payload2["data"]["results"]) > 0:
                second_page_created_ats = [item["created_at"] for item in payload2["data"]["results"]]
                assert set(first_page_created_ats).isdisjoint(set(second_page_created_ats))
        finally:
            await comm.disconnect()

    async def test_list_subscribe_validation_invalid_page(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "need_sync",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls9",
                        "query_params": {
                            "page": 0,
                            "size": 50,
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
                    "stream": "need_sync",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls10",
                        "query_params": {
                            "page": 1,
                            "size": 300,
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

    async def test_list_subscribe_validation_invalid_sort(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "need_sync",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls11",
                        "query_params": {
                            "sort_by": ["invalid_field"],
                            "page": 1,
                            "size": 50,
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

    async def test_list_subscribe_no_filters(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "need_sync",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls12",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "need_sync"
            assert payload["action"] == "list_subscribe"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert payload["data"]
            assert "results" in payload["data"]
            assert "count" in payload["data"]
        finally:
            await comm.disconnect()

    async def test_list_subscribe_large_size(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "need_sync",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls13",
                        "query_params": {
                            "page": 1,
                            "size": 200,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert len(payload["data"]["results"]) <= 200
            assert payload["data"]["count"] >= len(payload["data"]["results"])
        finally:
            await comm.disconnect()


import pytest
from access_manager.models import Card, NeedSyncDevice
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from main.models import Device


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestCardConsumer:

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

    async def test_list_basic(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r1",
                        "query_params": {
                            "page": 1,
                            "size": 20,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "cards"
            assert payload["action"] == "list"
            assert payload["request_id"] == "r1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert payload["data"]
            assert "results" in payload["data"]
            assert "count" in payload["data"]
            assert isinstance(payload["data"]["results"], list)
        finally:
            await comm.disconnect()

    async def test_list_empty_result(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r2",
                        "query_params": {
                            "page": 1,
                            "size": 20,
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

    async def test_list_default_sort(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r3",
                        "query_params": {
                            "page": 1,
                            "size": 20,
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

    async def test_list_sort_by_created_at_desc(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r4",
                        "query_params": {
                            "sort_by": ["-created_at"],
                            "page": 1,
                            "size": 20,
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

    async def test_list_sort_by_created_at_asc(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r5",
                        "query_params": {
                            "sort_by": ["created_at"],
                            "page": 1,
                            "size": 20,
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

    async def test_list_search_value(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r6",
                        "query_params": {
                            "search_value": "12",
                            "page": 1,
                            "size": 20,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            results = payload["data"]["results"]
            for item in results:
                assert item["number"].lower().startswith("12")
        finally:
            await comm.disconnect()

    async def test_list_search_value_no_match(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r7",
                        "query_params": {
                            "search_value": "nonexistent999",
                            "page": 1,
                            "size": 20,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert len(payload["data"]["results"]) == 0
        finally:
            await comm.disconnect()

    async def test_list_search_value_case_insensitive(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r8",
                        "query_params": {
                            "search_value": "12",
                            "page": 1,
                            "size": 20,
                        },
                    },
                }
            )
            reply1 = await comm.receive_json_from()
            payload1 = reply1.get("payload") or {}
            count1 = payload1["data"]["count"]

            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r9",
                        "query_params": {
                            "search_value": "12",
                            "page": 1,
                            "size": 20,
                        },
                    },
                }
            )
            reply2 = await comm.receive_json_from()
            payload2 = reply2.get("payload") or {}
            count2 = payload2["data"]["count"]

            assert count1 == count2
            results1 = payload1["data"]["results"]
            results2 = payload2["data"]["results"]
            for item in results1:
                assert item["number"].lower().startswith("12")
            for item in results2:
                assert item["number"].lower().startswith("12")
        finally:
            await comm.disconnect()

    async def test_list_filter_need_sync_true(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            card = await database_sync_to_async(Card.objects.filter(is_active=True).first)()
            if card:
                device = await database_sync_to_async(Device.objects.first)()
                if device:
                    await database_sync_to_async(NeedSyncDevice.objects.create)(
                        card=card,
                        device=device,
                        need_sync=True,
                    )

            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r10",
                        "query_params": {
                            "filters": {"need_sync": True},
                            "page": 1,
                            "size": 20,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            results = payload["data"]["results"]
            for item in results:
                assert item["need_to_sync"] is True
        finally:
            await comm.disconnect()

    async def test_list_filter_need_sync_false(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r11",
                        "query_params": {
                            "filters": {"need_sync": False},
                            "page": 1,
                            "size": 20,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            results = payload["data"]["results"]
            for item in results:
                assert item["need_to_sync"] is False
        finally:
            await comm.disconnect()

    async def test_list_filter_need_sync_combined_with_search(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r12",
                        "query_params": {
                            "search_value": "12",
                            "filters": {"need_sync": False},
                            "page": 1,
                            "size": 20,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            results = payload["data"]["results"]
            for item in results:
                assert item["need_to_sync"] is False
                assert item["number"].lower().startswith("12")
        finally:
            await comm.disconnect()

    async def test_list_pagination(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r13",
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

    async def test_list_pagination_page_2(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r14",
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
            first_page_ids = [item["card_id"] for item in payload1["data"]["results"]]

            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r15",
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
                second_page_ids = [item["card_id"] for item in payload2["data"]["results"]]
                assert set(first_page_ids).isdisjoint(set(second_page_ids))
        finally:
            await comm.disconnect()



    async def test_list_validation_invalid_sort(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r18",
                        "query_params": {
                            "sort_by": ["invalid_field"],
                            "page": 1,
                            "size": 20,
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

    async def test_list_no_filters(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r19",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "cards"
            assert payload["action"] == "list"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert payload["data"]
            assert "results" in payload["data"]
            assert "count" in payload["data"]
        finally:
            await comm.disconnect()

    async def test_list_large_size(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r20",
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

    async def test_list_tenant_scoping(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r21",
                        "query_params": {
                            "page": 1,
                            "size": 20,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            results = payload["data"]["results"]
            tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"
            all_cards = await database_sync_to_async(list)(
                Card.objects.filter(tenant_id=tenant_id, is_active=True).values_list("number", flat=True)
            )
            result_ids = [item["number"] for item in results]
            for card_id in result_ids:
                assert card_id in all_cards
        finally:
            await comm.disconnect()

    async def test_list_combined_filters(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r22",
                        "query_params": {
                            "search_value": "12",
                            "sort_by": ["-created_at"],
                            "filters": {"need_sync": False},
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
            for item in results:
                assert item["need_to_sync"] is False
                assert item["number"].lower().startswith("12")
            if len(results) > 1:
                for i in range(len(results) - 1):
                    assert results[i]["created_at"] >= results[i + 1]["created_at"]
        finally:
            await comm.disconnect()

    async def test_list_subscribe_basic(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls1",
                        "query_params": {
                            "page": 1,
                            "size": 20,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "cards"
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

    async def test_list_subscribe_with_filters(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls2",
                        "query_params": {
                            "search_value": "12",
                            "filters": {"need_sync": False},
                            "page": 1,
                            "size": 20,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            results = payload["data"]["results"]
            for item in results:
                assert item["need_to_sync"] is False
                assert item["number"].lower().startswith("12")
        finally:
            await comm.disconnect()

    async def test_list_subscribe_pagination(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls3",
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


    async def test_list_null_search_value(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r24",
                        "query_params": {
                            "search_value": None,
                            "page": 1,
                            "size": 20,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
        finally:
            await comm.disconnect()

    async def test_list_empty_filters(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r25",
                        "query_params": {
                            "filters": {},
                            "page": 1,
                            "size": 20,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
        finally:
            await comm.disconnect()

    async def test_list_unknown_filter_key(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "cards",
                    "payload": {
                        "action": "list",
                        "request_id": "r26",
                        "query_params": {
                            "filters": {"unknown_key": True},
                            "page": 1,
                            "size": 20,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
        finally:
            await comm.disconnect()

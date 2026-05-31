import uuid

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from main.models import Guest, Room


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestGuestConsumer:
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
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r1",
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

            assert stream == "guests"
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
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r2",
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

    async def test_list_filter_by_room(self, ws_connect, karina_token):
        room = await database_sync_to_async(Room.objects.first)()
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r3",
                        "query_params": {
                            "room": str(room.id) if room else None,
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
            for item in results:
                guest = await database_sync_to_async(Guest.objects.filter(id=item["id"], is_active=True).first)()
                if guest and room:
                    assert guest.room_id == room.id
        finally:
            await comm.disconnect()

    async def test_list_filter_by_different_room(self, ws_connect, karina_token):
        rooms = await database_sync_to_async(list)(Room.objects.all()[:2])
        if len(rooms) >= 2:
            room1, room2 = rooms[0], rooms[1]
            comm = await ws_connect(karina_token)
            try:
                await comm.send_json_to(
                    {
                        "stream": "guests",
                        "payload": {
                            "action": "list",
                            "request_id": "r4",
                            "query_params": {
                                "room": str(room1.id),
                                "page": 1,
                                "size": 50,
                            },
                        },
                    }
                )
                reply1 = await comm.receive_json_from()
                payload1 = reply1.get("payload") or {}
                results1_ids = [item["id"] for item in payload1["data"]["results"]]

                await comm.send_json_to(
                    {
                        "stream": "guests",
                        "payload": {
                            "action": "list",
                            "request_id": "r5",
                            "query_params": {
                                "room": str(room2.id),
                                "page": 1,
                                "size": 50,
                            },
                        },
                    }
                )
                reply2 = await comm.receive_json_from()
                payload2 = reply2.get("payload") or {}
                results2_ids = [item["id"] for item in payload2["data"]["results"]]

                assert set(results1_ids).isdisjoint(set(results2_ids))
            finally:
                await comm.disconnect()

    async def test_list_sort_by_created_at_desc(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r6",
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

    async def test_list_sort_by_created_at_asc(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r7",
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

    async def test_list_sort_by_name_asc(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r8",
                        "query_params": {
                            "sort_by": ["name"],
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
                    current_name = results[i].get("name", "")
                    next_name = results[i + 1].get("name", "")
                    assert current_name <= next_name
        finally:
            await comm.disconnect()

    async def test_list_sort_by_name_desc(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r9",
                        "query_params": {
                            "sort_by": ["-name"],
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
                    current_name = results[i].get("name", "")
                    next_name = results[i + 1].get("name", "")
                    assert current_name >= next_name
        finally:
            await comm.disconnect()

    async def test_list_sort_by_lastname_asc(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r10",
                        "query_params": {
                            "sort_by": ["lastname"],
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
                    current_lastname = results[i].get("lastname") or ""
                    next_lastname = results[i + 1].get("lastname") or ""
                    assert current_lastname <= next_lastname
        finally:
            await comm.disconnect()

    async def test_list_sort_by_lastname_desc(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r11",
                        "query_params": {
                            "sort_by": ["-lastname"],
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
                    current_lastname = results[i].get("lastname") or ""
                    next_lastname = results[i + 1].get("lastname") or ""
                    assert current_lastname >= next_lastname
        finally:
            await comm.disconnect()

    async def test_list_sort_by_gender_asc(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r12",
                        "query_params": {
                            "sort_by": ["gender"],
                            "page": 1,
                            "size": 50,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
        finally:
            await comm.disconnect()

    async def test_list_sort_by_nationality_asc(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r13",
                        "query_params": {
                            "sort_by": ["nationality"],
                            "page": 1,
                            "size": 50,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
        finally:
            await comm.disconnect()

    async def test_list_pagination(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
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
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r15",
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
            first_page_ids = [item["id"] for item in payload1["data"]["results"]]

            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r16",
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
                second_page_ids = [item["id"] for item in payload2["data"]["results"]]
                assert set(first_page_ids).isdisjoint(set(second_page_ids))
        finally:
            await comm.disconnect()

    async def test_list_validation_invalid_sort(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r17",
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

    async def test_list_validation_invalid_room(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r18",
                        "query_params": {
                            "room": "00000000-0000-0000-0000-000000000000",
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

    async def test_list_no_filters(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
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

            assert stream == "guests"
            assert payload["action"] == "list"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert payload["data"]
            assert "results" in payload["data"]
            assert "count" in payload["data"]
        finally:
            await comm.disconnect()

    async def test_list_tenant_scoping(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r20",
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
            tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"
            all_guest_ids = await database_sync_to_async(list)(
                Guest.objects.filter(tenant_id=tenant_id, is_active=True).values_list("id", flat=True)
            )
            result_ids = [item["id"] for item in results]
            for guest_id in result_ids:
                assert uuid.UUID(guest_id) in all_guest_ids
        finally:
            await comm.disconnect()

    async def test_list_only_active(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r21",
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
            for item in results:
                guest = await database_sync_to_async(Guest.objects.get)(id=item["id"])
                assert guest.is_active is True
        finally:
            await comm.disconnect()

    async def test_list_combined_filters(self, ws_connect, karina_token):
        room = await database_sync_to_async(Room.objects.first)()
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r22",
                        "query_params": {
                            "room": str(room.id) if room else None,
                            "sort_by": ["-created_at"],
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
                    assert results[i]["created_at"] >= results[i + 1]["created_at"]
        finally:
            await comm.disconnect()

    async def test_list_subscribe_basic(self, ws_connect, karina_token):
        room = await database_sync_to_async(Room.objects.first)()
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls1",
                        "query_params": {
                            "room": str(room.id) if room else None,
                            "page": 1,
                            "size": 50,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "guests"
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
        room = await database_sync_to_async(Room.objects.first)()
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls2",
                        "query_params": {
                            "room": str(room.id) if room else None,
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
                    assert results[i]["created_at"] >= results[i + 1]["created_at"]
        finally:
            await comm.disconnect()

    async def test_list_subscribe_pagination(self, ws_connect, karina_token):
        room = await database_sync_to_async(Room.objects.first)()
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls3",
                        "query_params": {
                            "room": str(room.id) if room else None,
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

    async def test_list_empty_sort_by(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r23",
                        "query_params": {
                            "sort_by": [],
                            "page": 1,
                            "size": 50,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
        finally:
            await comm.disconnect()

    async def test_list_large_size(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r24",
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

    async def test_list_multiple_sort_fields(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "guests",
                    "payload": {
                        "action": "list",
                        "request_id": "r25",
                        "query_params": {
                            "sort_by": ["-created_at", "name"],
                            "page": 1,
                            "size": 50,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
        finally:
            await comm.disconnect()

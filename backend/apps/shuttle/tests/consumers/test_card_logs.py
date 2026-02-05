import asyncio
from datetime import datetime

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from access_manager.models import AccessGroupChoices, CardLog
from main.models import Device, Guest, PublicSpace, Room


@pytest.fixture
@database_sync_to_async
def test_data():
    device = Device.objects.get(pk="a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    device2 = Device.objects.get(pk="b2c3d4e5-f6a7-8901-bcde-f12345678901")
    guest = Guest.objects.get(pk="5b66af57-fb27-4c26-9986-b9994e644605")
    room = Room.objects.get(pk="df77f910-2dcd-45cf-b6be-054c744561a7")
    return {"device": device, "device2": device2, "guest": guest, "room": room}


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestCardLogConsumer:

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

    async def test_list_subscribe_basic(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
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

            assert stream == "card_logs"
            assert payload["action"] == "list_subscribe"
            assert payload["request_id"] == "ls1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert payload["data"]
            assert "results" in payload["data"]
            assert "count" in payload["data"]
            assert isinstance(payload["data"]["results"], list)
            assert len(payload["data"]["results"]) > 0
        finally:
            await comm.disconnect()

    async def test_list_subscribe_filter_by_room(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls2",
                        "query_params": {
                            "room": str(test_data["room"].id),
                            "page": 1,
                            "size": 50,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert payload["data"]["results"]
            for result in payload["data"]["results"]:
                assert result.get("room_number") is not None
        finally:
            await comm.disconnect()

    async def test_list_subscribe_filter_by_card_num(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls3",
                        "query_params": {
                            "card_num": "12 23 34 45",
                            "page": 1,
                            "size": 50,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert payload["data"]["results"]
            for result in payload["data"]["results"]:
                assert result["number"] == "12 23 34 45"
        finally:
            await comm.disconnect()

    async def test_list_subscribe_filter_by_user(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls4",
                        "query_params": {
                            "user": str(test_data["guest"].id),
                            "page": 1,
                            "size": 50,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert payload["data"]["results"]
            guest_id_str = str(test_data["guest"].id).replace("-", "")
            for result in payload["data"]["results"]:
                assert result["user_id"].replace("-", "") == guest_id_str
        finally:
            await comm.disconnect()

    async def test_list_subscribe_filter_by_room_ids(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls6",
                        "query_params": {
                            "room_ids": [str(test_data["room"].id)],
                            "page": 1,
                            "size": 50,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert payload["data"]["results"]
        finally:
            await comm.disconnect()

    async def test_list_subscribe_filter_by_date_range(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls7",
                        "query_params": {
                            "filters": {
                                "from_date": "2025-01-15 09:00:00",
                                "to_date": "2025-01-15 14:00:00",
                            },
                            "page": 1,
                            "size": 50,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert payload["data"]["results"]
        finally:
            await comm.disconnect()

    async def test_list_subscribe_filter_combinations(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls8",
                        "query_params": {
                            "room": str(test_data["room"].id),
                            "card_num": "12 23 34 45",
                            "filters": {
                                "from_date": "2025-01-15 09:00:00",
                            },
                            "page": 1,
                            "size": 50,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert payload["data"]["results"]
        finally:
            await comm.disconnect()

    async def test_list_subscribe_pagination(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls9",
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

            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls10",
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
        finally:
            await comm.disconnect()

    async def test_list_subscribe_sort_by_event_ts_desc(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls11",
                        "query_params": {
                            "sort_by": ["-event_ts"],
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
                    current_ts = datetime.fromisoformat(results[i]["event_ts"].replace("Z", "+00:00"))
                    next_ts = datetime.fromisoformat(results[i + 1]["event_ts"].replace("Z", "+00:00"))
                    assert current_ts >= next_ts
        finally:
            await comm.disconnect()

    async def test_list_subscribe_sort_by_event_ts_asc(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls12",
                        "query_params": {
                            "sort_by": ["event_ts"],
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
                    current_ts = datetime.fromisoformat(results[i]["event_ts"].replace("Z", "+00:00"))
                    next_ts = datetime.fromisoformat(results[i + 1]["event_ts"].replace("Z", "+00:00"))
                    assert current_ts <= next_ts
        finally:
            await comm.disconnect()

    async def test_list_subscribe_validation_invalid_page(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls13",
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

    async def test_list_subscribe_validation_invalid_size(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls14",
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

    async def test_list_subscribe_validation_invalid_sort(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls15",
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

    async def test_list_subscribe_validation_invalid_date_format(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls16",
                        "query_params": {
                            "filters": {
                                "from_date": "invalid-date",
                            },
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

    async def test_list_subscribe_empty_result(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls17",
                        "query_params": {
                            "card_num": "nonexistent_card",
                            "page": 1,
                            "size": 50,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert payload["data"]["results"] == []
            assert payload["data"]["count"] == 0
        finally:
            await comm.disconnect()

    async def test_list_subscribe_default_sort(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls18",
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
                    current_ts = datetime.fromisoformat(results[i]["event_ts"].replace("Z", "+00:00"))
                    next_ts = datetime.fromisoformat(results[i + 1]["event_ts"].replace("Z", "+00:00"))
                    assert current_ts >= next_ts
        finally:
            await comm.disconnect()

    async def test_list_subscribe_filter_by_multiple_device_ids(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls20",
                        "query_params": {
                            "device_ids": [str(test_data["device"].id), str(test_data["device2"].id)],
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
            device_ids = {str(test_data["device"].id), str(test_data["device2"].id)}
            for result in results:
                assert result["device_id"] in device_ids
        finally:
            await comm.disconnect()

    async def test_list_subscribe_filter_by_public_space_ids(self, ws_connect, karina_token, test_data):
        public_space = await database_sync_to_async(PublicSpace.objects.first)()
        if public_space:
            comm = await ws_connect(karina_token)
            try:
                await comm.send_json_to(
                    {
                        "stream": "card_logs",
                        "payload": {
                            "action": "list_subscribe",
                            "request_id": "ls21",
                            "query_params": {
                                "public_space_ids": [str(public_space.id)],
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

    async def test_list_subscribe_filter_by_public_space(self, ws_connect, karina_token, test_data):
        public_space = await database_sync_to_async(PublicSpace.objects.first)()
        if public_space:
            comm = await ws_connect(karina_token)
            try:
                await comm.send_json_to(
                    {
                        "stream": "card_logs",
                        "payload": {
                            "action": "list_subscribe",
                            "request_id": "ls22",
                            "query_params": {
                                "public_space": str(public_space.id),
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

    async def test_list_subscribe_tenant_scoping(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls23",
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
            all_card_logs = await database_sync_to_async(list)(
                CardLog.objects.filter(device__tenant_id=tenant_id).values_list("id", flat=True)
            )
            result_ids = [item.get("id") for item in results if item.get("id")]
            for card_log_id in result_ids:
                if card_log_id:
                    assert card_log_id in all_card_logs
        finally:
            await comm.disconnect()

    async def test_list_subscribe_combined_all_filters(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls24",
                        "query_params": {
                            "room": str(test_data["room"].id),
                            "room_ids": [str(test_data["room"].id)],
                            "device_ids": [str(test_data["device"].id)],
                            "user": str(test_data["guest"].id),
                            "card_num": "12 23 34 45",
                            "filters": {
                                "from_date": "2025-01-15 09:00:00",
                                "to_date": "2025-01-15 14:00:00",
                            },
                            "sort_by": ["-event_ts"],
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
            for result in results:
                assert result["number"] == "12 23 34 45"
                assert result["device_id"] == str(test_data["device"].id)
            if len(results) > 1:
                for i in range(len(results) - 1):
                    current_ts = datetime.fromisoformat(results[i]["event_ts"].replace("Z", "+00:00"))
                    next_ts = datetime.fromisoformat(results[i + 1]["event_ts"].replace("Z", "+00:00"))
                    assert current_ts >= next_ts
        finally:
            await comm.disconnect()

    async def test_list_subscribe_empty_filters(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls25",
                        "query_params": {
                            "filters": {},
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

    async def test_list_subscribe_empty_lists(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls26",
                        "query_params": {
                            "device_ids": [],
                            "room_ids": [],
                            "public_space_ids": [],
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

    async def test_list_subscribe_from_date_only(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls27",
                        "query_params": {
                            "filters": {
                                "from_date": "2025-01-15 09:00:00",
                            },
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

    async def test_list_subscribe_to_date_only(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls28",
                        "query_params": {
                            "filters": {
                                "to_date": "2025-01-15 14:00:00",
                            },
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

    async def test_list_subscribe_large_size(self, ws_connect, karina_token, test_data):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "card_logs",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls29",
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

    async def test_list_subscribe_room_and_room_ids_combined(self, ws_connect, karina_token, test_data):
        rooms = await database_sync_to_async(list)(Room.objects.all()[:2])
        if len(rooms) >= 2:
            comm = await ws_connect(karina_token)
            try:
                await comm.send_json_to(
                    {
                        "stream": "card_logs",
                        "payload": {
                            "action": "list_subscribe",
                            "request_id": "ls30",
                            "query_params": {
                                "room": str(rooms[0].id),
                                "room_ids": [str(rooms[1].id)],
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

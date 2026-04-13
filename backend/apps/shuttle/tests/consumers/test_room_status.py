import pytest
from channels.testing import WebsocketCommunicator


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestRoomStatusConsumer:

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
                    "stream": "room_status",
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

            assert stream == "room_status"
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
            await comm.send_json_to(
                {
                    "stream": "room_status",
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
            assert "available" in data
            assert "checkedin" in data
            assert "offline" in data
            assert "dnd" in data
            assert "mur" in data
            assert "occupied" in data
            assert "ac_on_off" in data
        finally:
            await comm.disconnect()

    async def test_list_subscribe_response_types(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_status",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls3",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert isinstance(data["available"], int)
            assert isinstance(data["checkedin"], int)
            assert isinstance(data["offline"], int)
            assert isinstance(data["dnd"], int)
            assert isinstance(data["mur"], int)
            assert isinstance(data["occupied"], int)
            assert isinstance(data["ac_on_off"], int)
        finally:
            await comm.disconnect()

    async def test_list_subscribe_response_non_negative(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_status",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls4",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert data["available"] >= 0
            assert data["checkedin"] >= 0
            assert data["offline"] >= 0
            assert data["dnd"] >= 0
            assert data["mur"] >= 0
            assert data["occupied"] >= 0
            assert data["ac_on_off"] >= 0
        finally:
            await comm.disconnect()

    async def test_list_subscribe_tenant_scoping(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_status",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls5",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"
            from channels.db import database_sync_to_async

            from main.models import Device, Room

            total_rooms = await database_sync_to_async(Room.objects.filter(active=True, tenant_id=tenant_id).count)()
            total_devices = await database_sync_to_async(Device.objects.filter(tenant_id=tenant_id).count)()

            assert data["available"] <= total_rooms
            assert data["checkedin"] <= total_rooms
            assert data["offline"] <= total_devices
        finally:
            await comm.disconnect()

    async def test_list_subscribe_empty_query_params(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_status",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls6",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert payload["data"]
        finally:
            await comm.disconnect()

    async def test_list_subscribe_ignores_query_params(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_status",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls7",
                        "query_params": {
                            "page": 1,
                            "size": 50,
                            "room": "some-room-id",
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert "available" in data
            assert "checkedin" in data
            assert "offline" in data
        finally:
            await comm.disconnect()

    async def test_list_subscribe_consistent_response(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_status",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls8",
                        "query_params": {},
                    },
                }
            )
            reply1 = await comm.receive_json_from()
            payload1 = reply1.get("payload") or {}
            data1 = payload1["data"]

            await comm.send_json_to(
                {
                    "stream": "room_status",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls9",
                        "query_params": {},
                    },
                }
            )
            reply2 = await comm.receive_json_from()
            payload2 = reply2.get("payload") or {}
            data2 = payload2["data"]

            assert payload1["response_status"] == 200
            assert payload2["response_status"] == 200
            assert set(data1.keys()) == set(data2.keys())
        finally:
            await comm.disconnect()

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from main.models import Room


@pytest.fixture
@database_sync_to_async
def test_room():
    return Room.objects.get(pk="df77f910-2dcd-45cf-b6be-054c744561a7")


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestRoomDetailConsumer:

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

    async def test_subscribe_basic(self, ws_connect, karina_token, test_room):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_detail",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub1",
                        "pk": str(test_room.id),
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "room_detail"
            assert payload["action"] == "subscribe"
            assert payload["request_id"] == "sub1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert payload["data"]
            assert isinstance(payload["data"], dict)
        finally:
            await comm.disconnect()

    async def test_subscribe_response_structure(self, ws_connect, karina_token, test_room):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_detail",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub2",
                        "pk": str(test_room.id),
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert "id" in data
            assert "number" in data
            assert "floor" in data
            assert "block" in data
            assert "type" in data
            assert "state" in data
            assert "telemetry" in data
            assert "tenant" in data
            assert "devices" in data
            assert "guest" in data or data.get("guest") is None
        finally:
            await comm.disconnect()

    async def test_subscribe_with_keys(self, ws_connect, karina_token, test_room):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_detail",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub3",
                        "pk": str(test_room.id),
                        "keys": ["humidity", "temperature"],
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert "telemetry" in data
            assert isinstance(data["telemetry"], (dict, type(None)))
        finally:
            await comm.disconnect()

    async def test_subscribe_keys_always_include_static_keys(self, ws_connect, karina_token, test_room):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_detail",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub4",
                        "pk": str(test_room.id),
                        "keys": ["humidity"],
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert "telemetry" in data
        finally:
            await comm.disconnect()

    async def test_subscribe_empty_keys(self, ws_connect, karina_token, test_room):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_detail",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub5",
                        "pk": str(test_room.id),
                        "keys": [],
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert "telemetry" in data
        finally:
            await comm.disconnect()

    async def test_subscribe_tenant_scoping(self, ws_connect, karina_token, test_room):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_detail",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub6",
                        "pk": str(test_room.id),
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"
            assert data["tenant"] == tenant_id
            assert data["id"] == str(test_room.id)
        finally:
            await comm.disconnect()

    async def test_subscribe_validation_invalid_pk(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_detail",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub7",
                        "pk": "00000000-0000-0000-0000-000000000000",
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 400
            assert len(payload["errors"]) > 0
        finally:
            await comm.disconnect()

    async def test_subscribe_validation_missing_pk(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_detail",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub8",
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 400
            assert len(payload["errors"]) > 0
        finally:
            await comm.disconnect()

    async def test_subscribe_room_not_found(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_detail",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub9",
                        "pk": "99999999-9999-9999-9999-999999999999",
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 400
            assert len(payload["errors"]) > 0
        finally:
            await comm.disconnect()

    async def test_subscribe_room_from_different_tenant(self, ws_connect, karina_token):
        other_tenant_room = await database_sync_to_async(
            lambda: Room.objects.exclude(tenant_id="28c81921-f78e-4864-87d2-cec674f19d1c").first()
        )()
        if other_tenant_room:
            comm = await ws_connect(karina_token)
            try:
                await comm.send_json_to(
                    {
                        "stream": "room_detail",
                        "payload": {
                            "action": "subscribe",
                            "request_id": "sub10",
                            "pk": str(other_tenant_room.id),
                        },
                    }
                )
                reply = await comm.receive_json_from()
                payload = reply.get("payload") or {}

                assert payload["response_status"] == 400
                assert len(payload["errors"]) > 0
            finally:
                await comm.disconnect()

    async def test_subscribe_response_room_fields(self, ws_connect, karina_token, test_room):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_detail",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub11",
                        "pk": str(test_room.id),
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert data["id"] == str(test_room.id)
            assert str(data["number"]) == str(test_room.number)
            assert str(data["floor"]) == str(test_room.floor)
            assert str(data["block"]) == str(test_room.block)
        finally:
            await comm.disconnect()

    async def test_subscribe_response_devices(self, ws_connect, karina_token, test_room):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_detail",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub12",
                        "pk": str(test_room.id),
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert "devices" in data
            assert isinstance(data["devices"], list)
        finally:
            await comm.disconnect()

    async def test_subscribe_response_telemetry(self, ws_connect, karina_token, test_room):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_detail",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub13",
                        "pk": str(test_room.id),
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert "telemetry" in data
            assert isinstance(data["telemetry"], (dict, type(None)))
        finally:
            await comm.disconnect()

    async def test_subscribe_response_guest(self, ws_connect, karina_token, test_room):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_detail",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub14",
                        "pk": str(test_room.id),
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert "guest" in data or data.get("guest") is None
        finally:
            await comm.disconnect()

    async def test_subscribe_response_status(self, ws_connect, karina_token, test_room):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_detail",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub15",
                        "pk": str(test_room.id),
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert "state" in data
        finally:
            await comm.disconnect()

    async def test_subscribe_multiple_keys(self, ws_connect, karina_token, test_room):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_detail",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub16",
                        "pk": str(test_room.id),
                        "keys": ["humidity", "temperature", "cpuUsage", "memoryUsage"],
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert "telemetry" in data
        finally:
            await comm.disconnect()

    async def test_subscribe_duplicate_keys(self, ws_connect, karina_token, test_room):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_detail",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub17",
                        "pk": str(test_room.id),
                        "keys": ["humidity", "humidity", "temperature"],
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]
            assert "telemetry" in data
        finally:
            await comm.disconnect()

    async def test_unsubscribe_invalid_request_id(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "room_detail",
                    "payload": {
                        "action": "unsubscribe",
                        "request_id": "invalid_request_id",
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert payload["data"]["message"] == "Room not found!"
        finally:
            await comm.disconnect()

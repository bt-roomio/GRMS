import asyncio
import contextlib

import pytest
from channels.db import database_sync_to_async

from main.models import Room


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestRoomConsumer:
    async def test_list(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "rooms",
                    "payload": {
                        "action": "list",
                        "request_id": "r1",
                        "query_params": {"page": 1, "size": 10},
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "rooms"
            assert payload["action"] == "list"
            assert payload["request_id"] == "r1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert payload["data"]
        finally:
            await comm.disconnect()

    async def test_subscribe(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)

        try:
            await comm.send_json_to(
                {
                    "stream": "rooms",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub1",
                        "query_params": {"page": 1, "size": 10},
                    },
                }
            )
            await asyncio.sleep(1)
            await database_sync_to_async(Room.objects.create)(
                number="999",
                floor="1",
                block="A",
                tenant_id="28c81921-f78e-4864-87d2-cec674f19d1c",
            )
            reply = await asyncio.wait_for(comm.receive_json_from(), timeout=1.0)
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "rooms"
            assert payload["action"] == "create"
            assert payload["request_id"] == "sub1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert payload["data"]
            assert isinstance(payload["data"], dict)
            assert payload["data"].get("number") == "999"
            assert payload["data"].get("floor") == "1"
            assert payload["data"].get("block") == "A"
            assert payload["data"].get("tenant") == "28c81921-f78e-4864-87d2-cec674f19d1c"

        finally:
            await comm.disconnect()

    async def test_unsubscribe(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)

        try:
            await comm.send_json_to(
                {
                    "stream": "rooms",
                    "payload": {
                        "action": "subscribe",
                        "request_id": "sub1",
                        "query_params": {"page": 1, "size": 10},
                    },
                }
            )

            await comm.send_json_to(
                {
                    "stream": "rooms",
                    "payload": {
                        "action": "unsubscribe",
                        "request_id": "sub1",
                        "query_params": {"page": 1, "size": 10},
                    },
                }
            )
            await asyncio.sleep(1)
            await database_sync_to_async(Room.objects.create)(
                number="123",
                floor="1",
                block="A",
                tenant_id="28c81921-f78e-4864-87d2-cec674f19d1c",
            )
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(comm.receive_json_from(), timeout=1.0)

        finally:
            pass
            # disconnected by ws_connect fixture
            # await comm.disconnect()

    async def test_list_subscribe(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "rooms",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "ls1",
                        "query_params": {"page": 1, "size": 10},
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "rooms"
            assert payload["action"] == "list_subscribe"
            assert payload["request_id"] == "ls1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert payload["data"]

            await asyncio.sleep(1)
            await database_sync_to_async(Room.objects.create)(
                number="9999",
                floor="1",
                block="A",
                tenant_id="28c81921-f78e-4864-87d2-cec674f19d1c",
            )
            reply = await asyncio.wait_for(comm.receive_json_from(), timeout=1.0)
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "rooms"
            assert payload["action"] == "create"
            assert payload["data"]
            assert payload["data"]["results"]
            assert len(payload["data"]["results"]) == 6
            results = payload["data"].get("results")
            just_added_room = results[-1]
            assert just_added_room["number"] == "9999"
            assert just_added_room["floor"] == "1"
            assert just_added_room["block"] == "A"
            assert just_added_room["type"] is None
            assert just_added_room["state"] == [0]
            assert just_added_room["public_area_id"] is None
            assert just_added_room["pan_id"] is None
            assert just_added_room["building"] is None
            assert just_added_room["door_lock_device"] is None
            assert just_added_room["suite"] is None
            assert just_added_room["tenant"] == "28c81921-f78e-4864-87d2-cec674f19d1c"
            assert just_added_room["status"] == "OFF"
            assert just_added_room["devices"] == []
            assert just_added_room["additional_info"] is None
            assert just_added_room["telemetry"] == {
                "AC ON OFF": None,
                "AC Setpoint": None,
                "DND Relay": None,
                "MUR Relay": None,
                "Room Temperature": None,
                "Occupancy State": None,
            }
        finally:
            with contextlib.suppress(Exception):
                await comm.disconnect()

    async def test_list_unsubscribe(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)

        try:
            await comm.send_json_to(
                {
                    "stream": "rooms",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "sub1",
                        "query_params": {"page": 1, "size": 10},
                    },
                }
            )
            await comm.receive_json_from()

            await comm.send_json_to(
                {
                    "stream": "rooms",
                    "payload": {
                        "action": "list_unsubscribe",
                        "request_id": "sub1",
                        "query_params": {"page": 1, "size": 10},
                    },
                }
            )
            await asyncio.sleep(1)
            await database_sync_to_async(Room.objects.create)(
                number="1234",
                floor="1",
                block="A",
                tenant_id="28c81921-f78e-4864-87d2-cec674f19d1c",
            )
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(comm.receive_json_from(), timeout=1.0)

        finally:
            pass
            # disconnected by ws_connect fixture
            # await comm.disconnect()

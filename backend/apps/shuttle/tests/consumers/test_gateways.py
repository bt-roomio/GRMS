import asyncio

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from main.models import Device
from shuttle.models import AttributeKv


@pytest.fixture
@database_sync_to_async
def test_gateway_device():
    return Device.objects.get(pk="c3d4e5f6-a7b8-9012-cdef-123456789012")


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestGatewayConsumer:

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
                    "stream": "gateways",
                    "payload": {
                        "action": "list",
                        "request_id": "r1",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "gateways"
            assert payload["action"] == "list"
            assert payload["request_id"] == "r1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert payload["data"]
            assert isinstance(payload["data"], list)
            # We expect at least the fixture gateway device
            assert any(d["id"] == "c3d4e5f6-a7b8-9012-cdef-123456789012" for d in payload["data"])

            gateway = next(d for d in payload["data"] if d["id"] == "c3d4e5f6-a7b8-9012-cdef-123456789012")
            assert gateway["name"] == "Gateway Device 1"
            assert "total_connectors" in gateway
            assert "status" in gateway
        finally:
            await comm.disconnect()

    async def test_list_status_true(self, ws_connect, karina_token):
        # The fixture device has active=True attribute
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "gateways",
                    "payload": {
                        "action": "list",
                        "request_id": "r2",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            gateway = next(d for d in payload["data"] if d["id"] == "c3d4e5f6-a7b8-9012-cdef-123456789012")
            assert gateway["status"] is True
        finally:
            await comm.disconnect()

    async def test_list_excludes_non_gateway_devices(self, ws_connect, karina_token):
        # Attribute Test Device (pk=a1b2c3d4...) is NOT a gateway
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "gateways",
                    "payload": {
                        "action": "list",
                        "request_id": "r3",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            # Use 'a1b2c3d4...' from device.yaml which is NOT a gateway
            non_gateway_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
            assert not any(d["id"] == non_gateway_id for d in payload["data"])
        finally:
            await comm.disconnect()

    async def test_list_subscribe_basic(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "gateways",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "sub1",
                        "query_params": {},
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["action"] == "list_subscribe"
            assert payload["response_status"] == 200
            assert "results" in payload["data"]
            assert any(d["id"] == "c3d4e5f6-a7b8-9012-cdef-123456789012" for d in payload["data"]["results"])
        finally:
            await comm.disconnect()

    async def test_list_subscribe_receives_update(self, ws_connect, karina_token, test_gateway_device):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "gateways",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "sub2",
                        "query_params": {"page": 1, "size": 15},
                    },
                }
            )
            await comm.receive_json_from()

            attr = await database_sync_to_async(AttributeKv.objects.get)(
                entity=test_gateway_device, attribute_key="active", attribute_type=AttributeKv.SERVER_SCOPE
            )
            attr.bool_v = False
            await database_sync_to_async(attr.save)()

            reply = await asyncio.wait_for(comm.receive_json_from(), timeout=2.0)
            payload = reply.get("payload") or {}

            assert payload["action"] == "list_subscribe"
            assert "results" in payload["data"]
            gateway = next(d for d in payload["data"]["results"] if d["id"] == str(test_gateway_device.id))
            assert gateway["status"] is False

        finally:
            await comm.disconnect()

    async def test_list_unsubscribe(self, ws_connect, karina_token, test_gateway_device):
        comm = await ws_connect(karina_token)
        try:
            # Subscribe
            await comm.send_json_to(
                {
                    "stream": "gateways",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "sub3",
                        "query_params": {},
                    },
                }
            )
            await comm.receive_json_from()

            # Unsubscribe
            await comm.send_json_to(
                {
                    "stream": "gateways",
                    "payload": {
                        "action": "list_unsubscribe",
                        "request_id": "sub3",
                        "query_params": {},
                    },
                }
            )
            # Unsubscribe doesn't strictly send a reply in some consumers, but base might not?
            # GatewayConsumer.list_unsubscribe just removes group and pops.
            # It DOES NOT return anything.

            # Verify no updates received
            attr = await database_sync_to_async(AttributeKv.objects.get)(
                entity=test_gateway_device, attribute_key="active", attribute_type=AttributeKv.SERVER_SCOPE
            )
            attr.bool_v = True
            await database_sync_to_async(attr.save)()

            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(comm.receive_json_from(), timeout=1.0)

        finally:
            # Ensure disconnect to clean up
            try:
                await comm.disconnect()
            except asyncio.CancelledError:
                pass

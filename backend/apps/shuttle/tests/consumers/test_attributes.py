import uuid

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from main.models import Device
from shuttle.models import AttributeKv


@pytest.fixture
@database_sync_to_async
def test_devices():
    device = Device.objects.get(pk="a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    device2 = Device.objects.get(pk="b2c3d4e5-f6a7-8901-bcde-f12345678901")
    return {"device": device, "device2": device2}


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestAttributeConsumer:

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

    async def test_list_basic(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "attributes",
                    "payload": {
                        "action": "list",
                        "request_id": "r1",
                        "query_params": {
                            "device": str(test_devices["device"].id),
                            "scope": AttributeKv.CLIENT_SCOPE,
                            "page": 1,
                            "size": 25,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "attributes"
            assert payload["action"] == "list"
            assert payload["request_id"] == "r1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert payload["data"]
            assert isinstance(payload["data"], list)
            assert len(payload["data"]) == 2
            assert any(item["key_name"] == "ip_address" for item in payload["data"])
            assert any(item["key_name"] == "mac_address" for item in payload["data"])
        finally:
            await comm.disconnect()

    async def test_list_filter_by_scope(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "attributes",
                    "payload": {
                        "action": "list",
                        "request_id": "r2",
                        "query_params": {
                            "device": str(test_devices["device"].id),
                            "scope": AttributeKv.SHARED_SCOPE,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert len(payload["data"]) == 1
            assert payload["data"][0]["key_name"] == "roomNumber"
            assert payload["data"][0]["value"] in ("101", 101)
        finally:
            await comm.disconnect()

    async def test_list_filter_by_device(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "attributes",
                    "payload": {
                        "action": "list",
                        "request_id": "r3",
                        "query_params": {
                            "device": str(test_devices["device2"].id),
                            "scope": AttributeKv.CLIENT_SCOPE,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert len(payload["data"]) == 1
            assert payload["data"][0]["key_name"] == "ip_address"
            assert payload["data"][0]["value"] == "192.168.1.200"
        finally:
            await comm.disconnect()

    async def test_list_pagination(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "attributes",
                    "payload": {
                        "action": "list",
                        "request_id": "r4",
                        "query_params": {
                            "device": str(test_devices["device"].id),
                            "scope": AttributeKv.CLIENT_SCOPE,
                            "page": 1,
                            "size": 1,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert len(payload["data"]) == 1

            await comm.send_json_to(
                {
                    "stream": "attributes",
                    "payload": {
                        "action": "list",
                        "request_id": "r5",
                        "query_params": {
                            "device": str(test_devices["device"].id),
                            "scope": AttributeKv.CLIENT_SCOPE,
                            "page": 2,
                            "size": 1,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert len(payload["data"]) == 1
        finally:
            await comm.disconnect()

    async def test_list_sort_by_key_name_asc(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "attributes",
                    "payload": {
                        "action": "list",
                        "request_id": "r6",
                        "query_params": {
                            "device": str(test_devices["device"].id),
                            "scope": AttributeKv.CLIENT_SCOPE,
                            "sort_by": ["key_name"],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert len(payload["data"]) == 2
            assert payload["data"][0]["key_name"] == "ip_address"
            assert payload["data"][1]["key_name"] == "mac_address"
        finally:
            await comm.disconnect()

    async def test_list_sort_by_key_name_desc(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "attributes",
                    "payload": {
                        "action": "list",
                        "request_id": "r7",
                        "query_params": {
                            "device": str(test_devices["device"].id),
                            "scope": AttributeKv.CLIENT_SCOPE,
                            "sort_by": ["-key_name"],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert len(payload["data"]) == 2
            assert payload["data"][0]["key_name"] == "mac_address"
            assert payload["data"][1]["key_name"] == "ip_address"
        finally:
            await comm.disconnect()

    async def test_list_sort_by_last_update_ts_desc(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "attributes",
                    "payload": {
                        "action": "list",
                        "request_id": "r8",
                        "query_params": {
                            "device": str(test_devices["device"].id),
                            "scope": AttributeKv.CLIENT_SCOPE,
                            "sort_by": ["-last_update_ts"],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert len(payload["data"]) == 2
            assert all("last_update_ts" in item for item in payload["data"])
        finally:
            await comm.disconnect()

    async def test_list_multiple_sort_fields(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "attributes",
                    "payload": {
                        "action": "list",
                        "request_id": "r9",
                        "query_params": {
                            "device": str(test_devices["device"].id),
                            "scope": AttributeKv.CLIENT_SCOPE,
                            "sort_by": ["-last_update_ts", "key_name"],
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert len(payload["data"]) == 2
        finally:
            await comm.disconnect()

    async def test_list_validation_missing_device(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "attributes",
                    "payload": {
                        "action": "list",
                        "request_id": "r10",
                        "query_params": {
                            "scope": AttributeKv.CLIENT_SCOPE,
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

    async def test_list_validation_missing_scope(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "attributes",
                    "payload": {
                        "action": "list",
                        "request_id": "r11",
                        "query_params": {
                            "device": str(test_devices["device"].id),
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

    async def test_list_validation_invalid_scope(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "attributes",
                    "payload": {
                        "action": "list",
                        "request_id": "r12",
                        "query_params": {
                            "device": str(test_devices["device"].id),
                            "scope": "INVALID_SCOPE",
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

    async def test_list_validation_invalid_device(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "attributes",
                    "payload": {
                        "action": "list",
                        "request_id": "r13",
                        "query_params": {
                            "device": str(uuid.uuid4()),
                            "scope": AttributeKv.CLIENT_SCOPE,
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

    async def test_list_validation_invalid_page(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "attributes",
                    "payload": {
                        "action": "list",
                        "request_id": "r14",
                        "query_params": {
                            "device": str(test_devices["device"].id),
                            "scope": AttributeKv.CLIENT_SCOPE,
                            "page": 0,
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

    async def test_list_validation_invalid_size(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "attributes",
                    "payload": {
                        "action": "list",
                        "request_id": "r15",
                        "query_params": {
                            "device": str(test_devices["device"].id),
                            "scope": AttributeKv.CLIENT_SCOPE,
                            "size": 1000,
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

    async def test_list_empty_result(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "attributes",
                    "payload": {
                        "action": "list",
                        "request_id": "r17",
                        "query_params": {
                            "device": str(test_devices["device"].id),
                            "scope": AttributeKv.SERVER_SCOPE,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            assert len(payload["data"]) == 1
            assert payload["data"][0]["key_name"] == "active"
            assert payload["data"][0]["value"] is True
        finally:
            await comm.disconnect()

    async def test_list_value_types(self, ws_connect, karina_token, test_devices):
        comm = await ws_connect(karina_token)
        try:
            await database_sync_to_async(AttributeKv.objects.create)(
                entity=test_devices["device"],
                entity_type="DEVICE",
                attribute_type=AttributeKv.CLIENT_SCOPE,
                attribute_key="bool_attr",
                bool_v=True,
            )

            await database_sync_to_async(AttributeKv.objects.create)(
                entity=test_devices["device"],
                entity_type="DEVICE",
                attribute_type=AttributeKv.CLIENT_SCOPE,
                attribute_key="long_attr",
                long_v=12345,
            )

            await database_sync_to_async(AttributeKv.objects.create)(
                entity=test_devices["device"],
                entity_type="DEVICE",
                attribute_type=AttributeKv.CLIENT_SCOPE,
                attribute_key="dbl_attr",
                dbl_v=3.14,
            )

            await database_sync_to_async(AttributeKv.objects.create)(
                entity=test_devices["device"],
                entity_type="DEVICE",
                attribute_type=AttributeKv.CLIENT_SCOPE,
                attribute_key="json_attr",
                json_v={"nested": {"key": "value"}},
            )

            await comm.send_json_to(
                {
                    "stream": "attributes",
                    "payload": {
                        "action": "list",
                        "request_id": "r18",
                        "query_params": {
                            "device": str(test_devices["device"].id),
                            "scope": AttributeKv.CLIENT_SCOPE,
                        },
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            data = payload["data"]

            bool_item = next((item for item in data if item["key_name"] == "bool_attr"), None)
            assert bool_item is not None
            assert bool_item["value"] is True

            long_item = next((item for item in data if item["key_name"] == "long_attr"), None)
            assert long_item is not None
            assert long_item["value"] == 12345

            dbl_item = next((item for item in data if item["key_name"] == "dbl_attr"), None)
            assert dbl_item is not None
            assert dbl_item["value"] == 3.14

            json_item = next((item for item in data if item["key_name"] == "json_attr"), None)
            assert json_item is not None
            assert json_item["value"] == {"nested": {"key": "value"}}
        finally:
            await comm.disconnect()

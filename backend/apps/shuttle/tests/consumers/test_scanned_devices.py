import asyncio

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from main.models import Device
from shuttle.models import AttributeKv


async def _prepare_configuration() -> Device:
    device = await database_sync_to_async(Device.objects.get)(pk="c3d4e5f6-a7b8-9012-cdef-123456789012")

    config = {
        "configurationJson": {
            "devices": [
                {
                    "macAddress": "AA:BB:CC:DD:EE:01",
                    "addressMapId": 1,
                    "lastIp": "10.0.0.1",
                    "tempDevice": False,
                },
                {
                    "macAddress": "AA:BB:CC:DD:EE:02",
                    "addressMapId": 2,
                    "lastIp": "10.0.0.2",
                    "tempDevice": False,
                },
            ],
            "addressMaps": [
                {"addressMapId": 1, "addressMapName": "Floor 1"},
                {"addressMapId": 2, "addressMapName": "Floor 2"},
            ],
        }
    }

    await database_sync_to_async(AttributeKv.objects.update_or_create)(
        entity=device,
        entity_type="DEVICE",
        attribute_type=AttributeKv.SHARED_SCOPE,
        attribute_key="test_connector",
        defaults={"json_v": config},
    )

    return device


def _build_query(entity_id: str, **overrides) -> dict:
    base_query = {
        "entity_id": entity_id,
        "connector_name": "test_connector",
        "query": {
            "filters": {},
            "page_link": {
                "page": 1,
                "size": 10,
                "search_field": None,
                "search_text": None,
                "sort_by": [],
            },
        },
    }
    base_query.update(overrides)
    return base_query


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestScannedDevicesConsumer:
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
        device = await _prepare_configuration()
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "scanned_devices",
                    "payload": {
                        "action": "list",
                        "request_id": "sd1",
                        "query_params": _build_query(str(device.id)),
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "scanned_devices"
            assert payload["action"] == "list"
            assert payload["request_id"] == "sd1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []

            data = payload["data"]
            assert "devices" in data
            assert isinstance(data["devices"], list)
            assert len(data["devices"]) == 2

            first = data["devices"][0]
            assert "mac_address" in first
            assert "ip_address" in first
            assert "address_map" in first
            assert "exist_in_configuration" in first
            assert "status" in first
        finally:
            await comm.disconnect()

    async def test_list_filters_by_mac_address_prefix(self, ws_connect, karina_token):
        device = await _prepare_configuration()
        comm = await ws_connect(karina_token)
        try:
            query = _build_query(
                str(device.id),
                query={
                    "filters": {"mac_address": "AA:BB:CC:DD:EE:01"},
                    "page_link": {"page": 1, "size": 10},
                },
            )

            await comm.send_json_to(
                {
                    "stream": "scanned_devices",
                    "payload": {
                        "action": "list",
                        "request_id": "sd2",
                        "query_params": query,
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            devices = payload["data"]["devices"]
            assert len(devices) == 1
            assert devices[0]["mac_address"] == "AA:BB:CC:DD:EE:01"
        finally:
            await comm.disconnect()

    async def test_list_search_by_ip_address(self, ws_connect, karina_token):
        device = await _prepare_configuration()
        comm = await ws_connect(karina_token)
        try:
            query = _build_query(
                str(device.id),
                query={
                    "filters": {},
                    "page_link": {
                        "page": 1,
                        "size": 10,
                        "search_field": "ip_address",
                        "search_text": "10.0.0.2",
                    },
                },
            )

            await comm.send_json_to(
                {
                    "stream": "scanned_devices",
                    "payload": {
                        "action": "list",
                        "request_id": "sd3",
                        "query_params": query,
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            devices = payload["data"]["devices"]
            assert len(devices) == 1
            assert devices[0]["ip_address"] == "10.0.0.2"
        finally:
            await comm.disconnect()

    async def test_list_sort_by_mac_address_desc(self, ws_connect, karina_token):
        device = await _prepare_configuration()
        comm = await ws_connect(karina_token)
        try:
            query = _build_query(
                str(device.id),
                query={
                    "filters": {},
                    "page_link": {
                        "page": 1,
                        "size": 10,
                        "sort_by": ["-mac_address"],
                    },
                },
            )

            await comm.send_json_to(
                {
                    "stream": "scanned_devices",
                    "payload": {
                        "action": "list",
                        "request_id": "sd4",
                        "query_params": query,
                    },
                }
            )
            reply = await comm.receive_json_from()
            payload = reply.get("payload") or {}

            assert payload["response_status"] == 200
            devices = payload["data"]["devices"]
            macs = [d["mac_address"] for d in devices]
            assert macs == sorted(macs, reverse=True)
        finally:
            await comm.disconnect()

    async def test_list_pagination(self, ws_connect, karina_token):
        device = await _prepare_configuration()
        comm = await ws_connect(karina_token)
        try:
            base_query = _build_query(str(device.id))

            first_page_query = dict(base_query)
            first_page_query["query"] = {
                "filters": {},
                "page_link": {"page": 1, "size": 1},
            }

            second_page_query = dict(base_query)
            second_page_query["query"] = {
                "filters": {},
                "page_link": {"page": 2, "size": 1},
            }

            await comm.send_json_to(
                {
                    "stream": "scanned_devices",
                    "payload": {
                        "action": "list",
                        "request_id": "sd5",
                        "query_params": first_page_query,
                    },
                }
            )
            reply1 = await comm.receive_json_from()
            devices1 = reply1["payload"]["data"]["devices"]

            await comm.send_json_to(
                {
                    "stream": "scanned_devices",
                    "payload": {
                        "action": "list",
                        "request_id": "sd6",
                        "query_params": second_page_query,
                    },
                }
            )
            reply2 = await comm.receive_json_from()
            devices2 = reply2["payload"]["data"]["devices"]

            assert len(devices1) <= 1
            assert len(devices2) <= 1
            if devices1 and devices2:
                assert devices1[0]["mac_address"] != devices2[0]["mac_address"]
        finally:
            await comm.disconnect()

    async def test_list_subscribe_basic(self, ws_connect, karina_token):
        device = await _prepare_configuration()
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "scanned_devices",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "sd_sub1",
                        "query_params": _build_query(str(device.id)),
                    },
                }
            )
            reply = await comm.receive_json_from()
            stream = reply["stream"]
            payload = reply.get("payload") or {}

            assert stream == "scanned_devices"
            assert payload["action"] == "list_subscribe"
            assert payload["request_id"] == "sd_sub1"
            assert payload["response_status"] == 200
            assert payload["errors"] == []
            assert "devices" in payload["data"]
        finally:
            await comm.disconnect()

    async def test_list_subscribe_receives_update_on_scan_status_change(self, ws_connect, karina_token):
        device = await _prepare_configuration()
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(
                {
                    "stream": "scanned_devices",
                    "payload": {
                        "action": "list_subscribe",
                        "request_id": "sd_sub2",
                        "query_params": _build_query(str(device.id)),
                    },
                }
            )
            await comm.receive_json_from()

            attr, _ = await database_sync_to_async(AttributeKv.objects.get_or_create)(
                entity=device,
                entity_type="DEVICE",
                attribute_type=AttributeKv.CLIENT_SCOPE,
                attribute_key="scan_status",
                defaults={"bool_v": False},
            )
            attr.bool_v = True
            await database_sync_to_async(attr.save)()

            reply = await asyncio.wait_for(comm.receive_json_from(), timeout=2.0)
            payload = reply.get("payload") or {}

            assert payload["action"] == "list_subscribe"
            assert payload["response_status"] == 200
            assert "devices" in payload["data"]
        finally:
            await comm.disconnect()

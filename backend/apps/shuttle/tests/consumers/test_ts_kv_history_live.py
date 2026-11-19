import asyncio
from datetime import timedelta

import pytest
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.core.cache import caches
from django.utils import timezone

from main.models import Device
from shuttle.models import TsKv, TsKvDictionary
from shuttle.services import ts_kv_history_cache as history_cache
from shuttle.services.ts_kv_history_cache import mark_devices_updated
from shuttle.v2_consumers.ts_kv_history import TsKvHistoryConsumer

DEVICE_ID = "47aef21b-6cc9-4ec5-8573-1a6f491940c0"


@pytest.fixture(autouse=True)
def fast_refresh(monkeypatch):
    monkeypatch.setattr(TsKvHistoryConsumer, "refresh_delay", 0.05)


@pytest.fixture(autouse=True)
async def drop_added_telemetry():
    """Rows written through database_sync_to_async are committed outside the test transaction,
    so they are deleted the same way."""
    started = timezone.now()
    await database_sync_to_async(_clear_history_cache)()
    yield
    await database_sync_to_async(lambda: TsKv.objects.filter(ts__gte=started).delete())()
    await database_sync_to_async(_clear_history_cache)()


def _clear_history_cache():
    """Cached charts would outlive the rows deleted above and leak into other tests."""
    caches[history_cache.CACHE_NAME].delete_pattern(f"{history_cache.KEY_PREFIX}:*")


ROOM_ID = "df77f910-2dcd-45cf-b6be-054c744561a7"


@database_sync_to_async
def _room_and_other_device() -> tuple[str, str]:
    """The device the consumer resolves for ROOM_ID, and another device of the same tenant."""
    room_device = Device.objects.filter(room__id=ROOM_ID, is_active=True).first()
    assert room_device is not None
    other = Device.objects.filter(tenant_id=room_device.tenant_id).exclude(pk=room_device.pk).first()
    assert other is not None
    return str(room_device.pk), str(other.pk)


@database_sync_to_async
def _add_telemetry(key: str, value: float, device_id: str = DEVICE_ID):
    TsKv.objects.create(
        entity=Device.objects.get(pk=device_id),
        key=TsKvDictionary.objects.get(key=key),
        ts=timezone.now(),
        dbl_v=value,
    )


def _subscribe_message(request_id: str, device_id: str = DEVICE_ID, **query_params) -> dict:
    start_ts = (timezone.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    return {
        "stream": "ts_kv_history",
        "payload": {
            "action": "list_subscribe",
            "request_id": request_id,
            "query_params": {
                "device": device_id,
                "start_ts": start_ts,
                "interval": "1 day",
                "limit": 3,
                "auto_fill": False,
                "agg": "Avg",
                "keys": ["temperature"],
                "sort_by": ["interval_ts"],
                **query_params,
            },
        },
    }


async def _group_size(group: str) -> int:
    # Tests run on InMemoryChannelLayer: groups are a dict of {group: {channel: expiry}}.
    return len(get_channel_layer().groups.get(group, {}))


def _update(key: str, device_id: str = DEVICE_ID) -> dict:
    return {"type": "ts_kv_activity", "updates": [{"entity": device_id, "key": key, "dbl_v": 1.0}]}


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestTsKvHistoryLive:
    async def test_new_telemetry_is_pushed(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            # Upper-case id: the client's spelling must not break matching with mq-async updates.
            await comm.send_json_to(_subscribe_message("live1", DEVICE_ID.upper()))
            first = (await comm.receive_json_from())["payload"]
            assert first["response_status"] == 200

            # The post_save signal sends ts_kv_activity to the device group itself.
            await _add_telemetry("temperature", 999.0)

            live = (await comm.receive_json_from(timeout=5))["payload"]
            assert live["request_id"] == "live1"
            assert live["action"] == "list_subscribe"
            assert live["data"] != first["data"]
        finally:
            await comm.disconnect()

    async def test_other_key_is_ignored(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(_subscribe_message("live2"))
            await comm.receive_json_from()

            await get_channel_layer().group_send(f"tskv_updates_{DEVICE_ID}", _update("humidity"))
            assert await comm.receive_nothing(timeout=0.5)
        finally:
            await comm.disconnect()

    async def test_unchanged_data_is_not_resent(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(_subscribe_message("live3"))
            await comm.receive_json_from()

            await get_channel_layer().group_send(f"tskv_updates_{DEVICE_ID}", _update("temperature"))
            assert await comm.receive_nothing(timeout=0.5)
        finally:
            await comm.disconnect()

    async def test_unsubscribed_request_is_not_refreshed(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(_subscribe_message("live4"))
            await comm.receive_json_from()
            await comm.send_json_to(
                {"stream": "ts_kv_history", "payload": {"action": "list_unsubscribe", "request_id": "live4"}}
            )
            await asyncio.sleep(0.1)  # list_unsubscribe sends no reply to wait for

            await _add_telemetry("temperature", 555.0)
            assert await comm.receive_nothing(timeout=0.5)
        finally:
            await comm.disconnect()

    async def test_room_subscription_follows_the_room_device(self, ws_connect, karina_token):
        room_device, other_device = await _room_and_other_device()
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(_subscribe_message("live5", other_device, room=ROOM_ID))
            first = (await comm.receive_json_from())["payload"]
            assert first["response_status"] == 200

            # Telemetry of the device named in "device" does not affect the room chart.
            await get_channel_layer().group_send(f"tskv_updates_{other_device}", _update("temperature", other_device))
            assert await comm.receive_nothing(timeout=0.5)

            await _add_telemetry("temperature", 777.0, room_device)
            live = (await comm.receive_json_from(timeout=5))["payload"]
            assert live["request_id"] == "live5"
            assert live["data"] != first["data"]
        finally:
            await comm.disconnect()

    async def test_series_follow_the_requested_key_order(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(_subscribe_message("order1", keys=["temperature", "humidity"]))
            first = (await comm.receive_json_from())["payload"]
            # Same chart, keys listed the other way round: served from the same cache entry.
            await comm.send_json_to(_subscribe_message("order2", keys=["humidity", "temperature"]))
            second = (await comm.receive_json_from())["payload"]

            assert list(first["data"]) == ["temperature", "humidity"]
            assert list(second["data"]) == ["humidity", "temperature"]
        finally:
            await comm.disconnect()

    async def test_invalid_params_are_rejected_before_joining_the_group(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            members_before = await _group_size(f"tskv_updates_{DEVICE_ID}")
            await comm.send_json_to(_subscribe_message("bad1", limit=5000))
            reply = (await comm.receive_json_from())["payload"]
            assert reply["response_status"] == 400
            assert await _group_size(f"tskv_updates_{DEVICE_ID}") == members_before
        finally:
            await comm.disconnect()

    async def test_stale_cached_chart_is_sent_then_refreshed(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(_subscribe_message("stale1"))
            first = (await comm.receive_json_from())["payload"]
            await comm.send_json_to(
                {"stream": "ts_kv_history", "payload": {"action": "list_unsubscribe", "request_id": "stale1"}}
            )
            await asyncio.sleep(0.1)
            await _add_telemetry("temperature", 888.0)
            # The signal marks the device on commit, which the test transaction never reaches.
            await database_sync_to_async(mark_devices_updated)([DEVICE_ID])

            await comm.send_json_to(_subscribe_message("stale2"))
            cached = (await comm.receive_json_from())["payload"]
            assert cached["data"] == first["data"]
            fresh = (await comm.receive_json_from(timeout=5))["payload"]
            assert fresh["request_id"] == "stale2"
            assert fresh["data"] != first["data"]
        finally:
            await comm.disconnect()

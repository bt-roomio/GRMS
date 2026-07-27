"""Unit tests for resolve_devices_batch (memory → MGET → DB tiers, mocked I/O)."""

from unittest.mock import AsyncMock, MagicMock, patch

from core.management.mq.devices import device_cache as dc
from core.management.mq.devices import device_resolver as dr
from core.management.mq.devices.device_resolver import resolve_devices_batch


def _clear():
    dc._DEVICE_MEMORY_CACHE.clear()


async def test_empty_input_returns_empty():
    assert await resolve_devices_batch([]) == {}


async def test_memory_hit_avoids_all_io():
    _clear()
    device = {"id": "d1", "name": "n", "tenant_id": "t", "device_profile_id": "p"}
    dc._update_memory_cache("d1", device)

    with patch.object(dr.redis_client, "mget", new=AsyncMock()) as mget:
        result = await resolve_devices_batch(["d1"])

    assert result == {"d1": device}
    mget.assert_not_awaited()


async def test_redis_hit_populates_memory():
    _clear()
    raw = b'{"id":"d1","name":"n","tenant_id":"t","device_profile_id":"p"}'
    with patch.object(dr.redis_client, "mget", new=AsyncMock(return_value=[raw])):
        result = await resolve_devices_batch(["d1"])

    assert result["d1"]["name"] == "n"
    assert "d1" in dc._DEVICE_MEMORY_CACHE  # promoted to memory tier


async def test_db_hit_and_miss():
    _clear()
    pipe = MagicMock()
    pipe.execute = AsyncMock()
    with (
        patch.object(dr.redis_client, "mget", new=AsyncMock(return_value=[None, None])),
        patch.object(dr.redis_client, "pipeline", return_value=pipe),
        patch.object(dr, "Device") as Device,
    ):
        Device.objects.filter.return_value.values.return_value = [
            {"id": "d1", "name": "n1", "tenant_id": "t1", "device_profile_id": "p1"},
        ]
        result = await resolve_devices_batch(["d1", "d2"])

    assert result["d1"]["name"] == "n1"
    assert result["d2"] is None  # not returned by the DB query
    pipe.set.assert_called_once()  # only the found device gets cached
    pipe.execute.assert_awaited_once()


async def test_composite_id_falls_back_to_single_resolver():
    _clear()
    with (
        patch.object(dr.redis_client, "mget", new=AsyncMock(return_value=[None])),
        patch.object(dr, "get_device", new=AsyncMock(return_value={"id": "sub"})) as get_device,
    ):
        result = await resolve_devices_batch(["gw&sub"])

    get_device.assert_awaited_once_with("gw&sub")
    assert result["gw&sub"] == {"id": "sub"}

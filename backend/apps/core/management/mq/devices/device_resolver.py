"""Async device resolution for the MQ consumer.

2-tier caching: in-memory (process-local) → Redis → PostgreSQL. Shares the
in-memory cache with the sync path (:mod:`core.management.mq.devices.get_device`) via
:mod:`core.management.mq.devices.device_cache`.
"""

import logging

import orjson
from asgiref.sync import sync_to_async
from django.db import close_old_connections

from core.management.mq.config import DEVICE_CACHE_EXPIRY
from core.management.mq.devices.device_cache import (
    _DEVICE_MEMORY_CACHE,
    _MEMORY_CACHE_TTL,
    DeviceType,
    _update_memory_cache,
    build_device_data,
    device_cache_key,
)
from core.utils.get_time import get_mil_sec
from core.utils.redis_pool import async_redis as redis_client
from main.models import Device

logger = logging.getLogger(__name__)


async def get_device(device_id: str, tenant_id=None) -> DeviceType | None:
    """Get device with 2-tier caching: memory → Redis → database (async version)"""
    # Tier 1: Check in-memory cache (fastest, no network)
    current_time = get_mil_sec() // 1000  # seconds
    cache_entry = _DEVICE_MEMORY_CACHE.get(device_id)
    if cache_entry and (current_time - cache_entry["cached_at"]) < _MEMORY_CACHE_TTL:
        return cache_entry["data"]

    # Tier 2: Check Redis cache
    cache_key = device_cache_key(device_id)
    cached_device_raw = await redis_client.get(cache_key)
    cached_device = cached_device_raw.decode("utf-8") if isinstance(cached_device_raw, bytes) else None

    if cached_device:
        logger.debug("Device found in Redis cache: %s", device_id)
        data = orjson.loads(cached_device)
        _update_memory_cache(device_id, data)
        return data

    # Tier 3: Database lookup
    filters = {"id": device_id}
    if "&" in device_id:
        filters = {"name": device_id.split("&")[1], "tenant_id": tenant_id, "is_active": True}

    def _get_device_from_db(_f=filters):
        close_old_connections()
        return Device.objects.filter(**_f).first()

    device = await sync_to_async(_get_device_from_db, thread_sensitive=False)()

    if not device:
        return None

    data = build_device_data(device.id, device.name, device.tenant_id, device.device_profile_id)

    await redis_client.set(cache_key, orjson.dumps(data), ex=DEVICE_CACHE_EXPIRY)
    logger.debug("Device cached from DB: %s", device_id)
    _update_memory_cache(device_id, data)

    return data


async def resolve_devices_batch(device_ids) -> dict[str, DeviceType | None]:
    """Resolve many devices at once: memory cache → one Redis MGET → one DB query.

    Replaces N per-message ``get_device()`` round-trips in the batch validation
    step. Composite "&" ids (sub-devices) are rare on the ingest path and fall
    back to the single-device resolver.
    """
    result: dict[str, DeviceType | None] = {}
    if not device_ids:
        return result

    now = get_mil_sec() // 1000  # seconds

    # Tier 1: memory cache
    redis_misses = []
    for device_id in device_ids:
        entry = _DEVICE_MEMORY_CACHE.get(device_id)
        if entry and (now - entry["cached_at"]) < _MEMORY_CACHE_TTL:
            result[device_id] = entry["data"]
        else:
            redis_misses.append(device_id)

    if not redis_misses:
        return result

    # Tier 2: one MGET for every memory miss
    cached_raws = await redis_client.mget([device_cache_key(d) for d in redis_misses])
    db_misses = []
    for device_id, raw in zip(redis_misses, cached_raws):
        if raw:
            data = orjson.loads(raw)
            _update_memory_cache(device_id, data)
            result[device_id] = data
        else:
            db_misses.append(device_id)

    if not db_misses:
        return result

    # Tier 3: one DB query for plain ids; composite "&" ids fall back individually
    plain_ids = [d for d in db_misses if "&" not in d]
    composite_ids = [d for d in db_misses if "&" in d]

    if plain_ids:

        def _query_devices(_ids=plain_ids):
            close_old_connections()
            return list(Device.objects.filter(id__in=_ids).values("id", "name", "tenant_id", "device_profile_id"))

        rows = await sync_to_async(_query_devices, thread_sensitive=False)()
        by_id = {str(row["id"]): row for row in rows}

        pipe = redis_client.pipeline()
        for device_id in plain_ids:
            row = by_id.get(device_id)
            if not row:
                result[device_id] = None
                continue
            data = build_device_data(row["id"], row["name"], row["tenant_id"], row["device_profile_id"])
            result[device_id] = data
            _update_memory_cache(device_id, data)
            pipe.set(device_cache_key(device_id), orjson.dumps(data), ex=DEVICE_CACHE_EXPIRY)
        await pipe.execute()

    for device_id in composite_ids:
        result[device_id] = await get_device(device_id)

    return result

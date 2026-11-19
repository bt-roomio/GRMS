"""Redis cache of the ts_kv_history WebSocket stream (aggregated chart data).

A cached entry is ``{"at": <time its computation started>, "data": ...}``. Writers of
``shuttle_ts_kv`` call :func:`mark_devices_updated`; an entry computed before the device's
latest write is *stale*. A new subscriber may get a stale entry at once (the consumer then
recomputes it in the background and pushes the difference), a live refresh never does.
An entry lives for a fraction of its bucket width (:func:`history_cache_ttl`), which bounds
staleness when writes are not marked (e.g. raw SQL imports).

Recomputation is single-flight: one consumer computes, the others viewing the same chart
wait for its result instead of running the same aggregate query.
"""

import asyncio
import datetime
import hashlib
import json
import logging
import time
from collections.abc import Callable, Iterable
from typing import Any

from asgiref.sync import sync_to_async
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.cache import caches
from django.utils import timezone
from django_redis.exceptions import ConnectionInterrupted
from redis.exceptions import RedisError

from shuttle.utils.fill_empty_intervals import parse_interval

logger = logging.getLogger(__name__)

CACHE_NAME = "default"
KEY_PREFIX = "ts_kv_history"
# Upper bound of one computation: a lock of a crashed process frees itself after this.
LOCK_TIMEOUT = 30
# How long a consumer waits for another one's computation before running its own.
WAIT_TIMEOUT = 10.0
POLL_INTERVAL = 0.1

CACHE_ERRORS = (ConnectionInterrupted, RedisError)


def history_cache_ttl(interval: str | None) -> int:
    """Lifetime of a cached chart, seconds: one 60th of the bucket width, clamped to
    [TSKV_HISTORY_CACHE_MIN_TTL, TSKV_HISTORY_CACHE_MAX_TTL]; 0 disables the cache."""
    min_ttl = settings.TSKV_HISTORY_CACHE_MIN_TTL
    max_ttl = settings.TSKV_HISTORY_CACHE_MAX_TTL
    if max_ttl <= 0:
        return 0
    if not interval:
        return min_ttl
    try:
        use_rd, delta_kwargs = parse_interval(interval)
    except ValueError:
        return min_ttl
    step = relativedelta(**delta_kwargs) if use_rd else datetime.timedelta(**delta_kwargs)
    origin = timezone.now()
    bucket_seconds = ((origin + step) - origin).total_seconds()
    return int(min(max(bucket_seconds // 60, min_ttl), max_ttl))


def history_cache_key(tenant_id, device_id: str, params: dict[str, Any]) -> str:
    start_ts = params.get("start_ts")
    fingerprint = {
        "keys": sorted(set(params.get("keys") or [])),
        "start_ts": start_ts.isoformat() if start_ts else None,
        "interval": params.get("interval"),
        "agg": params.get("agg"),
        "limit": params.get("limit"),
        "sort_by": params.get("sort_by"),
        "auto_fill": params.get("auto_fill"),
    }
    digest = hashlib.sha1(json.dumps(fingerprint, sort_keys=True).encode(), usedforsecurity=False).hexdigest()
    return f"{KEY_PREFIX}:{tenant_id}:{device_id}:{digest}"


def _updated_marker_key(device_id) -> str:
    return f"{KEY_PREFIX}:updated:{device_id}"


def mark_devices_updated(device_ids: Iterable) -> None:
    """Record that new ts_kv rows of these devices were committed just now."""
    max_ttl = settings.TSKV_HISTORY_CACHE_MAX_TTL
    device_ids = {str(device_id) for device_id in device_ids if device_id}
    if max_ttl <= 0 or not device_ids:
        return
    now = time.time()
    try:
        # Outlives every entry it can invalidate (they live at most max_ttl).
        caches[CACHE_NAME].set_many({_updated_marker_key(d): now for d in device_ids}, max_ttl + 5)
    except CACHE_ERRORS as exc:
        logger.warning("ts_kv_history: failed to mark %d device(s) as updated: %s", len(device_ids), exc)


async def _cached_entry(key: str, device_id: str, fresh_since: float | None) -> tuple[Any, bool]:
    """(cached data or None, whether it includes every write of the device and ``fresh_since``)."""
    marker_key = _updated_marker_key(device_id)
    try:
        values = await caches[CACHE_NAME].aget_many([key, marker_key])
    except CACHE_ERRORS as exc:
        logger.warning("ts_kv_history cache read failed: %s", exc)
        return None, False
    entry = values.get(key)
    if not isinstance(entry, dict) or "at" not in entry:
        return None, False
    return entry["data"], entry["at"] >= max(values.get(marker_key) or 0, fresh_since or 0)


async def _fresh_entry(key: str, device_id: str, fresh_since: float | None):
    data, fresh = await _cached_entry(key, device_id, fresh_since)
    return data if fresh else None


async def get_or_compute(
    key: str | None,
    device_id: str | None,
    ttl: int,
    compute: Callable[[], Any],
    fresh_since: float | None = None,
    allow_stale: bool = False,
) -> tuple[Any, bool]:
    """``(data, stale)``: cached chart data, or the result of ``compute`` (a sync callable)
    stored in the cache.

    ``fresh_since`` additionally rejects entries computed before that moment (the time
    a live telemetry event was received). With ``allow_stale`` an entry older than the
    device's latest write is returned as is, with ``stale=True``.
    """
    if not key or not device_id or ttl <= 0:
        return await sync_to_async(compute)(), False

    data, fresh = await _cached_entry(key, device_id, fresh_since)
    if data is not None and (fresh or allow_stale):
        return data, not fresh

    cache = caches[CACHE_NAME]
    lock_key = f"{key}:lock"
    try:
        locked = await cache.aadd(lock_key, 1, LOCK_TIMEOUT)
    except CACHE_ERRORS as exc:
        logger.warning("ts_kv_history cache lock failed: %s", exc)
        return await sync_to_async(compute)(), False

    if not locked:
        # Someone is computing this chart: wait for a result fresh enough for us.
        deadline = time.monotonic() + WAIT_TIMEOUT
        while time.monotonic() < deadline:
            await asyncio.sleep(POLL_INTERVAL)
            data = await _fresh_entry(key, device_id, fresh_since)
            if data is not None:
                return data, False
            try:
                released = not await cache.ahas_key(lock_key)
            except CACHE_ERRORS:
                break
            if released:
                # The result may have been stored right after our read above.
                data = await _fresh_entry(key, device_id, fresh_since)
                if data is not None:
                    return data, False
                # Started before our write/event (or failed): compute ourselves.
                break

    started_at = time.time()
    try:
        data = await sync_to_async(compute)()
        try:
            await cache.aset(key, {"at": started_at, "data": data}, ttl)
        except CACHE_ERRORS as exc:
            logger.warning("ts_kv_history cache write failed: %s", exc)
    finally:
        if locked:
            try:
                await cache.adelete(lock_key)
            except CACHE_ERRORS as exc:
                logger.warning("ts_kv_history cache unlock failed: %s", exc)
    return data, False

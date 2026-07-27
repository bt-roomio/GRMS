"""
Shared device caching module for MQ handlers.

This module provides a process-local in-memory cache for device lookups,
used by both sync and async message queue handlers to reduce Redis and
database query overhead.

2-tier caching strategy:
- Tier 1: Process-local memory cache (this module) - Fastest, no network
- Tier 2: Redis cache - Medium speed
- Tier 3: Database - Slowest, authoritative source
"""

import logging
import threading
from typing import TypedDict

from core.utils.get_time import get_mil_sec

logger = logging.getLogger(__name__)


class DeviceType(TypedDict):
    """Device data structure for caching"""

    id: str
    name: str
    tenant_id: str
    device_profile_id: str


def device_cache_key(device_id: str) -> str:
    """Single source of truth for the Redis device-cache key format (sync + async paths)."""
    return f"prs_msg:device_cache:{device_id}"


def build_device_data(device_id, name, tenant_id, device_profile_id) -> DeviceType:
    """Single source of truth for the cached DeviceType shape (sync + async paths)."""
    return {
        "id": str(device_id),
        "name": name,
        "tenant_id": str(tenant_id),
        "device_profile_id": str(device_profile_id),
    }


# Process-local in-memory cache (2-tier: memory → Redis → DB)
# Eliminates Redis roundtrip overhead for hot devices (1-2ms savings per lookup)
_DEVICE_MEMORY_CACHE = {}
_MEMORY_CACHE_MAX_SIZE = 10000  # Prevent unlimited memory growth
_MEMORY_CACHE_TTL = 300  # 5 minutes

# The cache is read from the event loop (async resolver) and written from both the
# loop and the sync thread pool (get_sub_device). Guard writes/eviction so the
# eviction's sorted() iteration can't race a concurrent mutation.
_cache_lock = threading.Lock()


def _update_memory_cache(device_id: str, data: DeviceType):
    """Update in-memory cache with size limit and eviction (thread-safe)."""
    with _cache_lock:
        if len(_DEVICE_MEMORY_CACHE) >= _MEMORY_CACHE_MAX_SIZE:
            # Evict oldest 10% of entries to prevent memory bloat
            sorted_entries = sorted(_DEVICE_MEMORY_CACHE.items(), key=lambda x: x[1]["cached_at"])
            evict_count = _MEMORY_CACHE_MAX_SIZE // 10
            for key, _ in sorted_entries[:evict_count]:
                del _DEVICE_MEMORY_CACHE[key]
            logger.debug("Evicted %d old entries from memory cache", evict_count)

        _DEVICE_MEMORY_CACHE[device_id] = {"data": data, "cached_at": get_mil_sec() // 1000}

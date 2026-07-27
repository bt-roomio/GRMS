"""Unit tests for the process-local device cache (key format, data shape, eviction, thread-safety)."""

import threading
from unittest.mock import patch
from uuid import UUID

from core.management.mq.devices import device_cache as dc


def _clear():
    dc._DEVICE_MEMORY_CACHE.clear()


def test_device_cache_key_format():
    assert dc.device_cache_key("abc") == "prs_msg:device_cache:abc"


def test_build_device_data_coerces_to_str():
    u = UUID("12345678-1234-5678-1234-567812345678")
    data = dc.build_device_data(u, "gw", u, u)
    assert data == {"id": str(u), "name": "gw", "tenant_id": str(u), "device_profile_id": str(u)}


def test_update_memory_cache_stores_entry():
    _clear()
    dc._update_memory_cache("d1", {"id": "d1"})
    entry = dc._DEVICE_MEMORY_CACHE["d1"]
    assert entry["data"] == {"id": "d1"}
    assert isinstance(entry["cached_at"], int)


def test_eviction_drops_oldest_when_full():
    _clear()
    with patch.object(dc, "_MEMORY_CACHE_MAX_SIZE", 10):
        for i in range(10):
            dc._update_memory_cache(f"d{i}", {"n": i})
        # cache is full (10 == max); the next insert evicts the oldest 10 // 10 == 1
        dc._update_memory_cache("d10", {"n": 10})
    assert "d0" not in dc._DEVICE_MEMORY_CACHE
    assert "d10" in dc._DEVICE_MEMORY_CACHE
    assert len(dc._DEVICE_MEMORY_CACHE) <= 10


def test_concurrent_updates_do_not_raise_under_eviction():
    """8 threads mutating while eviction's sorted() iterates must not raise."""
    _clear()
    errors = []

    def worker(base):
        try:
            for i in range(300):
                dc._update_memory_cache(f"{base}-{i}", {"n": i})
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    with patch.object(dc, "_MEMORY_CACHE_MAX_SIZE", 50):
        threads = [threading.Thread(target=worker, args=(b,)) for b in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert errors == []
    assert len(dc._DEVICE_MEMORY_CACHE) <= 50

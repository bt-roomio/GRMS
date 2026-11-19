import asyncio
from unittest import mock

import pytest
from django.core.cache import caches

from shuttle.services import ts_kv_history_cache as history_cache
from shuttle.services.ts_kv_history_cache import get_or_compute, history_cache_ttl, mark_devices_updated

# The package conftest loads fixtures into the DB for the whole session.
pytestmark = pytest.mark.django_db

DEVICE_ID = "00000000-0000-0000-0000-00000000c0de"
KEY = f"ts_kv_history:test:{DEVICE_ID}:chart"


@pytest.fixture(autouse=True)
def cache_settings(settings):
    settings.TSKV_HISTORY_CACHE_MIN_TTL = 30
    settings.TSKV_HISTORY_CACHE_MAX_TTL = 300
    return settings


@pytest.fixture
def clean_cache():
    cache = caches[history_cache.CACHE_NAME]
    keys = [KEY, f"{KEY}:lock", f"ts_kv_history:updated:{DEVICE_ID}"]
    cache.delete_many(keys)
    yield cache
    cache.delete_many(keys)


class TestHistoryCacheTtl:
    def test_hourly(self):
        assert history_cache_ttl("1 hour") == 60

    def test_daily_is_clamped_to_max(self):
        assert history_cache_ttl("1 day") == 300
        assert history_cache_ttl("month") == 300

    def test_short_interval_is_clamped_to_min(self):
        assert history_cache_ttl("1 minute") == 30

    def test_raw_values_and_bad_interval_use_min(self):
        assert history_cache_ttl(None) == 30
        assert history_cache_ttl("fortnight") == 30

    def test_disabled(self, cache_settings):
        cache_settings.TSKV_HISTORY_CACHE_MAX_TTL = 0
        assert history_cache_ttl("1 hour") == 0


@pytest.mark.asyncio
class TestGetOrCompute:
    async def test_second_call_is_served_from_cache(self, clean_cache):
        compute = mock.Mock(return_value={"t": [1]})
        assert await get_or_compute(KEY, DEVICE_ID, 60, compute) == ({"t": [1]}, False)
        assert await get_or_compute(KEY, DEVICE_ID, 60, compute) == ({"t": [1]}, False)
        assert compute.call_count == 1

    async def test_device_write_invalidates_entry(self, clean_cache):
        await get_or_compute(KEY, DEVICE_ID, 60, lambda: {"t": [1]})
        mark_devices_updated([DEVICE_ID])
        assert await get_or_compute(KEY, DEVICE_ID, 60, lambda: {"t": [2]}) == ({"t": [2]}, False)

    async def test_stale_entry_is_served_when_allowed(self, clean_cache):
        await get_or_compute(KEY, DEVICE_ID, 60, lambda: {"t": [1]})
        mark_devices_updated([DEVICE_ID])
        compute = mock.Mock(return_value={"t": [2]})
        assert await get_or_compute(KEY, DEVICE_ID, 60, compute, allow_stale=True) == ({"t": [1]}, True)
        compute.assert_not_called()

    async def test_fresh_since_rejects_older_entry(self, clean_cache):
        await get_or_compute(KEY, DEVICE_ID, 60, lambda: {"t": [1]})
        later = history_cache.time.time() + 1
        assert await get_or_compute(KEY, DEVICE_ID, 60, lambda: {"t": [2]}, fresh_since=later) == ({"t": [2]}, False)

    async def test_concurrent_requests_compute_once(self, clean_cache):
        calls = 0

        def compute():
            nonlocal calls
            calls += 1
            history_cache.time.sleep(0.3)
            return {"t": [calls]}

        results = await asyncio.gather(*(get_or_compute(KEY, DEVICE_ID, 60, compute) for _ in range(5)))
        assert calls == 1
        assert all(result == ({"t": [1]}, False) for result in results)

    async def test_disabled_cache_always_computes(self, clean_cache):
        compute = mock.Mock(return_value={})
        await get_or_compute(KEY, DEVICE_ID, 0, compute)
        await get_or_compute(KEY, DEVICE_ID, 0, compute)
        assert compute.call_count == 2

"""Unit tests for _resolve_device_profile_id (memory → Redis → filter-then-create)."""

from contextlib import nullcontext
from unittest.mock import MagicMock, patch

import pytest
from django.db import IntegrityError

from core.management.mq.devices import get_device as gd
from core.utils.get_time import get_mil_sec


def _clear():
    gd._PROFILE_MEMORY_CACHE.clear()


def test_memory_hit_avoids_redis():
    _clear()
    gd._PROFILE_MEMORY_CACHE["t1:ttlock"] = {"id": "p1", "cached_at": get_mil_sec() // 1000}
    with patch.object(gd.redis_client, "get") as rget:
        # "TTLock" lowercases to "ttlock" for the cache id
        assert gd._resolve_device_profile_id("t1", "TTLock") == "p1"
    rget.assert_not_called()


def test_redis_hit_populates_memory():
    _clear()
    with patch.object(gd.redis_client, "get", return_value=b"p2"):
        assert gd._resolve_device_profile_id("t1", "TTLock") == "p2"
    assert "t1:ttlock" in gd._PROFILE_MEMORY_CACHE


def test_db_filter_then_create_when_missing():
    _clear()
    created = MagicMock(id="p3")
    with (
        patch.object(gd.redis_client, "get", return_value=None),
        patch.object(gd.redis_client, "set") as rset,
        patch.object(gd.transaction, "atomic", side_effect=lambda *a, **k: nullcontext()),
        patch.object(gd, "DeviceProfile") as DeviceProfile,
    ):
        DeviceProfile.objects.filter.return_value.first.return_value = None
        DeviceProfile.objects.create.return_value = created
        assert gd._resolve_device_profile_id("t1", "TTLock") == "p3"

    DeviceProfile.objects.create.assert_called_once()
    rset.assert_called_once()


def test_db_existing_profile_is_not_recreated():
    _clear()
    existing = MagicMock(id="p4")
    with (
        patch.object(gd.redis_client, "get", return_value=None),
        patch.object(gd.redis_client, "set"),
        patch.object(gd, "DeviceProfile") as DeviceProfile,
    ):
        DeviceProfile.objects.filter.return_value.first.return_value = existing
        assert gd._resolve_device_profile_id("t1", "TTLock") == "p4"

    DeviceProfile.objects.create.assert_not_called()


def test_create_race_returns_existing_on_integrity_error():
    """Parallel replica created the profile → re-fetch instead of propagating IntegrityError."""
    _clear()
    existing = MagicMock(id="p5")
    with (
        patch.object(gd.redis_client, "get", return_value=None),
        patch.object(gd.redis_client, "set"),
        patch.object(gd.transaction, "atomic", side_effect=lambda *a, **k: nullcontext()),
        patch.object(gd, "DeviceProfile") as DeviceProfile,
    ):
        DeviceProfile.objects.filter.return_value.first.side_effect = [None, existing]
        DeviceProfile.objects.create.side_effect = IntegrityError("duplicate key")
        assert gd._resolve_device_profile_id("t1", "TTLock") == "p5"


def test_create_race_reraises_when_still_missing():
    _clear()
    with (
        patch.object(gd.redis_client, "get", return_value=None),
        patch.object(gd.redis_client, "set"),
        patch.object(gd.transaction, "atomic", side_effect=lambda *a, **k: nullcontext()),
        patch.object(gd, "DeviceProfile") as DeviceProfile,
    ):
        DeviceProfile.objects.filter.return_value.first.side_effect = [None, None]
        DeviceProfile.objects.create.side_effect = IntegrityError("duplicate key")
        with pytest.raises(IntegrityError):
            gd._resolve_device_profile_id("t1", "TTLock")

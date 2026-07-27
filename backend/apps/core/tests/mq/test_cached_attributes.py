"""Unit tests for get_cached_attributes_batch (MGET semantics, mocked Redis)."""

from unittest.mock import patch

from shuttle.utils import has_changed_and_update as h
from shuttle.utils.has_changed_and_update import get_cached_attributes_batch


def test_all_keys_present_is_hit():
    raws = [b'{"active":{"bool_v":true},"lastActivityTime":{"long_v":1}}']
    with patch.object(h.redis_client, "mget", return_value=raws) as mget:
        result = get_cached_attributes_batch(["d1"], ["active", "lastActivityTime"])
    mget.assert_called_once_with(["device_attrs:d1:SERVER_SCOPE"])
    assert result["d1"]["active"] == {"bool_v": True}


def test_partial_keys_is_miss():
    with patch.object(h.redis_client, "mget", return_value=[b'{"active":1}']):
        result = get_cached_attributes_batch(["d1"], ["active", "lastActivityTime"])
    assert result["d1"] is None


def test_missing_and_garbage_entries_are_none():
    with patch.object(h.redis_client, "mget", return_value=[None, b"not-json"]):
        result = get_cached_attributes_batch(["d1", "d2"], ["active"])
    assert result == {"d1": None, "d2": None}


def test_custom_scope_used_in_key():
    with patch.object(h.redis_client, "mget", return_value=[None]) as mget:
        get_cached_attributes_batch(["d1"], ["shared"], "SHARED_SCOPE")
    mget.assert_called_once_with(["device_attrs:d1:SHARED_SCOPE"])


def test_empty_ids_skips_redis():
    with patch.object(h.redis_client, "mget") as mget:
        assert get_cached_attributes_batch([], ["active"]) == {}
    mget.assert_not_called()

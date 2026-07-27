"""Unit tests for telemetry batch helpers (key collection, tskv-dict batch, fias callback)."""

from unittest.mock import MagicMock, patch

from core.management.mq.handlers import telemetry as t
from core.utils.get_time import get_mil_sec


def test_collect_value_keys_dict_form():
    keys = set()
    t._collect_value_keys({"ts": 1, "values": {"a": 1, "b": 2}}, keys)
    assert keys == {"a", "b"}


def test_collect_value_keys_list_form():
    keys = set()
    t._collect_value_keys([{"ts": 1, "values": {"x": 1}}, {"ts": 2, "values": {"y": 2}}], keys)
    assert keys == {"x", "y"}


def test_collect_value_keys_ignores_malformed():
    keys = set()
    t._collect_value_keys("garbage", keys)
    t._collect_value_keys({"no_values": 1}, keys)
    t._collect_value_keys([{"ts": 1}], keys)
    assert keys == set()


def test_collect_value_keys_drops_non_storable_values():
    """None-valued keys are dropped (find_compatible_field skips them), so warming never
    creates a TsKvDictionary row for a value that is never persisted."""
    keys = set()
    t._collect_value_keys({"ts": 1, "values": {"stored": 1, "skip": None}}, keys)
    assert keys == {"stored"}


def test_warm_excludes_none_valued_keys():
    batch = [(None, "v1/devices/me/telemetry", [{"ts": 1, "values": {"kept": 1, "dropped": None}}])]
    with patch.object(t, "get_tskv_dicts_batch") as batch_fn:
        t._warm_tskv_dict_cache(batch)
    batch_fn.assert_called_once()
    assert set(batch_fn.call_args[0][0]) == {"kept"}


def test_warm_collects_keys_and_excludes_rfid_card_event():
    batch = [
        (None, "v1/gateway/telemetry", {"sub1": [{"ts": 1, "values": {"temp": 1, "rfid_card_event": {}}}]}),
        (None, "v1/devices/me/telemetry", [{"ts": 2, "values": {"hum": 5}}]),
    ]
    with patch.object(t, "get_tskv_dicts_batch") as batch_fn:
        t._warm_tskv_dict_cache(batch)
    batch_fn.assert_called_once()
    assert set(batch_fn.call_args[0][0]) == {"temp", "hum"}


def test_warm_is_noop_when_no_keys():
    with patch.object(t, "get_tskv_dicts_batch") as batch_fn:
        t._warm_tskv_dict_cache([(None, "v1/devices/me/telemetry", [])])
    batch_fn.assert_not_called()


def test_get_tskv_dicts_batch_memory_hit_and_dedup():
    t._TSKV_DICT_MEMORY_CACHE.clear()
    t._TSKV_DICT_MEMORY_CACHE["Temperature"] = {
        "data": {"key_id": 7, "key": "Temperature"},
        "cached_at": get_mil_sec() // 1000,
    }
    with patch.object(t.redis_client, "mget") as mget:
        result = t.get_tskv_dicts_batch(["Temperature", "Temperature", ""])
    assert result == {"Temperature": {"key_id": 7, "key": "Temperature"}}
    mget.assert_not_called()  # fully served from memory


def test_get_tskv_dicts_batch_empty():
    assert t.get_tskv_dicts_batch([]) == {}


def test_get_tskv_dicts_batch_redis_hit_and_db_miss():
    t._TSKV_DICT_MEMORY_CACHE.clear()
    pipe = MagicMock()
    created = MagicMock(key_id=9, key="Humidity")
    with (
        patch.object(t.redis_client, "mget", return_value=[b'{"key_id":3,"key":"Temp"}', None]),
        patch.object(t.redis_client, "pipeline", return_value=pipe),
        patch.object(t.TsKvDictionary.objects, "get_or_create", return_value=(created, True)) as goc,
    ):
        result = t.get_tskv_dicts_batch(["Temp", "Humidity"])

    assert result["Temp"] == {"key_id": 3, "key": "Temp"}
    assert result["Humidity"] == {"key_id": 9, "key": "Humidity"}
    goc.assert_called_once_with(key="Humidity")
    pipe.set.assert_called_once()
    pipe.execute.assert_called_once()


def test_log_fias_result_logs_on_exception():
    future = MagicMock()
    future.exception.return_value = RuntimeError("boom")
    with patch.object(t.logger, "error") as error:
        t._log_fias_result(future)
    error.assert_called_once()


def test_log_fias_result_silent_on_success():
    future = MagicMock()
    future.exception.return_value = None
    with patch.object(t.logger, "error") as error:
        t._log_fias_result(future)
    error.assert_not_called()

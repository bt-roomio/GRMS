"""Unit tests for core.management.mq.engine.validation._extract_keys (pure, no I/O)."""

from core.management.mq.engine.validation import _extract_keys


def test_telemetry_list_form():
    data = [{"ts": 1, "values": {"temp": 1, "hum": 2}}, {"ts": 2, "values": {"co2": 3}}]
    assert set(_extract_keys("v1/devices/me/telemetry", data)) == {"temp", "hum", "co2"}


def test_telemetry_gateway_dict_form():
    data = {"sub1": [{"ts": 1, "values": {"a": 1}}], "sub2": [{"ts": 2, "values": {"b": 2}}]}
    assert set(_extract_keys("v1/gateway/telemetry", data)) == {"a", "b"}


def test_attributes_flat_form():
    data = {"online": True, "fw": "1.0"}
    assert set(_extract_keys("v1/devices/me/attributes", data)) == {"online", "fw"}


def test_attributes_nested_form():
    data = {"sub1": {"k1": 1}, "sub2": {"k2": 2}}
    assert set(_extract_keys("v1/gateway/attributes", data)) == {"k1", "k2"}


def test_unknown_topic_returns_empty():
    assert _extract_keys("v1/gateway/rpc", {"x": 1}) == []


def test_keys_are_deduped():
    data = [{"ts": 1, "values": {"t": 1}}, {"ts": 2, "values": {"t": 2}}]
    assert _extract_keys("x/telemetry", data) == ["t"]


def test_malformed_payload_is_safe():
    assert _extract_keys("x/telemetry", "garbage") == []
    assert _extract_keys("x/attributes", None) == []

"""Unit tests for BatchProcessor seams: _parse, _route grouping/metrics, _run_group status marking."""

from unittest.mock import AsyncMock, MagicMock

from core.management.mq.engine.processor import (
    STATUS_NO_REQUEUE,
    STATUS_REQUEUE,
    STATUS_SUCCESS,
    BatchProcessor,
)


def _msg(tag):
    m = MagicMock()
    m.delivery_tag = tag
    return m


def test_parse_marks_unparseable_no_requeue():
    p = BatchProcessor("q")
    bad = MagicMock(body=b"not-json", delivery_tag=7)
    status: dict = {}
    parsed, source_ids = p._parse([bad], status)
    assert parsed == []
    assert source_ids == set()
    assert status[7] == STATUS_NO_REQUEUE


def test_parse_collects_source_ids():
    p = BatchProcessor("q")
    import orjson

    good = MagicMock(body=orjson.dumps({"sourceDeviceUUID": "d1", "topic": "x/telemetry"}), delivery_tag=1)
    no_src = MagicMock(body=orjson.dumps({"topic": "x/telemetry"}), delivery_tag=2)
    status: dict = {}
    parsed, source_ids = p._parse([good, no_src], status)
    assert len(parsed) == 2
    assert source_ids == {"d1"}  # message without sourceDeviceUUID contributes no id


def test_route_groups_each_topic_family():
    p = BatchProcessor("q")
    device = {"id": "d1"}
    parsed = [
        (_msg(1), {"sourceDeviceUUID": "d1", "topic": "v1/devices/me/telemetry", "data": []}),
        (_msg(2), {"sourceDeviceUUID": "d1", "topic": "v1/gateway/attributes", "data": {}}),
        (_msg(3), {"sourceDeviceUUID": "d1", "topic": "v1/gateway/connect", "data": {}}),
        (_msg(4), {"sourceDeviceUUID": "d1", "topic": "v1/gateway/rpc", "data": {}}),
    ]
    status: dict = {}
    grouped = p._route(parsed, {"d1": device}, status)

    assert [len(grouped.telemetry), len(grouped.attributes)] == [1, 1]
    assert [len(grouped.device_connect), len(grouped.other)] == [1, 1]
    assert grouped.telemetry[0][:3] == (device, "v1/devices/me/telemetry", [])


def test_route_marks_unknown_device_no_requeue():
    p = BatchProcessor("q")
    status: dict = {}
    grouped = p._route([(_msg(9), {"sourceDeviceUUID": "missing", "topic": "x/telemetry", "data": []})], {}, status)
    assert status[9] == STATUS_NO_REQUEUE
    assert grouped.telemetry == []


async def test_run_group_marks_success_and_forwards_triples():
    p = BatchProcessor("q")
    handler = AsyncMock()
    items = [({"id": "d1"}, "x/telemetry", [1], _msg(1)), ({"id": "d2"}, "x/telemetry", [2], _msg(2))]
    status: dict = {}
    await p._run_group("Telemetry", items, handler, status)

    handler.assert_awaited_once()
    assert handler.await_args[0][0] == [({"id": "d1"}, "x/telemetry", [1]), ({"id": "d2"}, "x/telemetry", [2])]
    assert status == {1: STATUS_SUCCESS, 2: STATUS_SUCCESS}


async def test_run_group_requeues_on_handler_error():
    p = BatchProcessor("q")
    handler = AsyncMock(side_effect=RuntimeError("db down"))
    items = [({"id": "d1"}, "x/telemetry", [1], _msg(1))]
    status: dict = {}
    await p._run_group("Telemetry", items, handler, status)
    assert status == {1: STATUS_REQUEUE}


async def test_run_group_noop_on_empty():
    p = BatchProcessor("q")
    handler = AsyncMock()
    status: dict = {}
    await p._run_group("Telemetry", [], handler, status)
    handler.assert_not_awaited()
    assert status == {}

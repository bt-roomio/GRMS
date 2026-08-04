"""Integration tests for BatchAccumulator.process_batch: topic routing + ack/nack outcomes.

Every external dependency (device resolution, batch handlers) is mocked, so these run
without a database. They pin the message-lifecycle contract of the consumer.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import orjson

from core.management.mq.engine import processor as bp
from core.management.mq.engine.batch_processor import BatchAccumulator


def _message(body, tag):
    msg = MagicMock()
    msg.body = body if isinstance(body, bytes) else orjson.dumps(body)
    msg.delivery_tag = tag
    msg.ack = AsyncMock()
    msg.nack = AsyncMock()
    return msg


def _acc():
    return BatchAccumulator("q", batch_size=10, batch_timeout=0.1, publisher=MagicMock())


def _patch_handlers():
    """Patch resolve + all batch handlers; caller overrides individual return values."""
    return (
        patch.object(bp, "sync_telemetry_batch_async", new=AsyncMock()),
        patch.object(bp, "sync_attributes_batch_async", new=AsyncMock()),
        patch.object(bp, "sync_state_device_batch_async", new=AsyncMock()),
    )


async def test_telemetry_is_routed_and_acked():
    acc = _acc()
    device = {"id": "d1", "tenant_id": "t1"}
    msg = _message(
        {"sourceDeviceUUID": "d1", "topic": "v1/devices/me/telemetry", "data": [{"ts": 1, "values": {"a": 1}}]}, 1
    )
    tele, attrs, state = _patch_handlers()
    with (
        patch.object(bp, "resolve_devices_batch", new=AsyncMock(return_value={"d1": device})),
        tele as tele_m,
        attrs,
        state,
    ):
        await acc.process_batch([msg])

    tele_m.assert_awaited_once()
    routed = tele_m.await_args[0][0]  # [(device, topic, data)]
    assert routed[0][0] == device
    assert routed[0][1].endswith("/telemetry")
    msg.ack.assert_awaited_once()
    msg.nack.assert_not_awaited()


async def test_device_not_found_nacks_without_requeue():
    acc = _acc()
    msg = _message({"sourceDeviceUUID": "missing", "topic": "x/telemetry", "data": []}, 2)
    with patch.object(bp, "resolve_devices_batch", new=AsyncMock(return_value={"missing": None})):
        await acc.process_batch([msg])
    msg.nack.assert_awaited_once_with(requeue=False)
    msg.ack.assert_not_awaited()


async def test_unparseable_body_nacks_without_requeue():
    acc = _acc()
    msg = _message(b"not-json", 3)
    with patch.object(bp, "resolve_devices_batch", new=AsyncMock(return_value={})):
        await acc.process_batch([msg])
    msg.nack.assert_awaited_once_with(requeue=False)


async def test_handler_failure_requeues():
    acc = _acc()
    device = {"id": "d1", "tenant_id": "t1"}
    msg = _message({"sourceDeviceUUID": "d1", "topic": "x/telemetry", "data": []}, 4)
    _tele, attrs, state = _patch_handlers()
    failing = patch.object(bp, "sync_telemetry_batch_async", new=AsyncMock(side_effect=RuntimeError("db down")))
    with patch.object(bp, "resolve_devices_batch", new=AsyncMock(return_value={"d1": device})), failing, attrs, state:
        await acc.process_batch([msg])
    msg.nack.assert_awaited_once_with(requeue=True)
    msg.ack.assert_not_awaited()


async def test_connect_message_routed_to_state_handler():
    acc = _acc()
    device = {"id": "d1", "tenant_id": "t1"}
    msg = _message({"sourceDeviceUUID": "d1", "topic": "v1/gateway/connect", "data": {"device": "sub"}}, 5)
    tele, attrs, state = _patch_handlers()
    with (
        patch.object(bp, "resolve_devices_batch", new=AsyncMock(return_value={"d1": device})),
        tele,
        attrs,
        state as state_m,
    ):
        await acc.process_batch([msg])
    state_m.assert_awaited_once()
    msg.ack.assert_awaited_once()

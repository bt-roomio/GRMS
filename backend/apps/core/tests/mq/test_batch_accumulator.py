"""Unit tests for BatchAccumulator drain logic (async, no I/O)."""

from unittest.mock import MagicMock

from core.management.mq.engine.batch_processor import BatchAccumulator


def _acc(batch_size=3, batch_timeout=0.02):
    return BatchAccumulator("q", batch_size, batch_timeout, publisher=MagicMock())


async def test_collect_batch_caps_at_batch_size():
    acc = _acc(batch_size=3)
    for i in range(5):
        await acc.message_queue.put(f"m{i}")
    assert await acc._collect_batch() == ["m0", "m1", "m2"]
    # remaining stay queued
    assert acc.message_queue.qsize() == 2


async def test_collect_batch_drains_all_available_below_cap():
    acc = _acc(batch_size=10)
    for i in range(3):
        await acc.message_queue.put(i)
    assert await acc._collect_batch() == [0, 1, 2]


async def test_collect_batch_returns_empty_on_timeout():
    acc = _acc(batch_timeout=0.01)
    assert await acc._collect_batch() == []


async def test_drain_remaining_takes_everything_then_empty():
    acc = _acc()
    for i in range(4):
        await acc.message_queue.put(i)
    assert acc._drain_remaining() == [0, 1, 2, 3]
    assert acc._drain_remaining() == []

"""Unit tests for BatchAccumulator drain logic (async, no I/O)."""

import asyncio
import time
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


async def test_collect_batch_lingers_for_message_after_queue_empties():
    """Суть правки: сообщение, пришедшее в окне batch_timeout уже ПОСЛЕ того как
    очередь опустела, всё равно попадает в батч — не закрываемся на первой пустоте."""
    acc = _acc(batch_size=10, batch_timeout=0.2)
    await acc.message_queue.put("m0")

    async def _late_put():
        # Очередь опустеет после первого get; докидываем позже, но внутри окна.
        await asyncio.sleep(0.05)
        await acc.message_queue.put("m1")

    asyncio.create_task(_late_put())
    batch = await acc._collect_batch()
    assert batch == ["m0", "m1"]  # старое поведение вернуло бы только ["m0"]


async def test_collect_batch_stops_at_deadline_when_underfilled():
    """Не набрав batch_size и не дождавшись новых сообщений, батч закрывается по
    истечении batch_timeout от первого сообщения (а не висит бесконечно)."""
    acc = _acc(batch_size=100, batch_timeout=0.05)
    await acc.message_queue.put("only")

    started = time.monotonic()
    batch = await acc._collect_batch()
    elapsed = time.monotonic() - started

    assert batch == ["only"]
    assert elapsed >= 0.05  # дождались дедлайна, а не вышли мгновенно
    assert elapsed < 0.5  # но и не зависли

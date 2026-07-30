"""Unit tests for RoomStatusConsumer per-tenant response cache and trailing refresh.

These exercise the caching/coalescing logic directly (no channel layer, no DB):
_compute_response is stubbed and the module-level caches are cleared per test.
"""

import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from shuttle.v2_consumers import room_status as rs
from shuttle.v2_consumers.room_status import RoomStatusConsumer


@pytest.fixture(autouse=True)
def _clear_caches():
    rs._response_cache.clear()
    rs._response_locks.clear()
    yield
    rs._response_cache.clear()
    rs._response_locks.clear()


def _consumer(tenant="t1"):
    c = object.__new__(RoomStatusConsumer)
    c.subscribers = {}
    c.scope = {"user": {"tenant_id": tenant}}
    c._trailing = None
    return c


def _counting_compute():
    """Stub _compute_response: counts calls, small await to force interleaving."""
    state = {"n": 0}

    async def _compute(_tenant_id):
        state["n"] += 1
        await asyncio.sleep(0.01)
        return {"v": state["n"]}

    return state, _compute


async def test_response_caches_within_ttl():
    c = _consumer()
    state, c._compute_response = _counting_compute()

    first = await c.response()
    second = await c.response()

    assert first == second == {"v": 1}
    assert state["n"] == 1  # второй вызов обслужен из кеша


async def test_concurrent_first_computes_coalesce_to_one():
    """N подписчиков, кеш пуст: один пересчёт под локом, остальные переиспользуют."""
    c = _consumer()
    state, c._compute_response = _counting_compute()

    results = await asyncio.gather(*(c.response() for _ in range(5)))

    assert results == [{"v": 1}] * 5
    assert state["n"] == 1


async def test_force_reuses_fresh_cache():
    """Ключ коалесцирования trailing: force НЕ пересчитывает, если кеш свеж."""
    c = _consumer()
    state, c._compute_response = _counting_compute()

    await c.response()  # заполнили кеш, n=1
    forced = await c.response(force=True)

    assert forced == {"v": 1}
    assert state["n"] == 1  # force переиспользовал свежий кеш


async def test_force_recomputes_when_cache_stale():
    """force обязан увидеть свежее состояние, когда окно кеша истекло."""
    c = _consumer()
    state, c._compute_response = _counting_compute()

    await c.response()  # n=1
    # Искусственно состариваем метку кеша за пределы TTL.
    _ts, data = rs._response_cache["t1"]
    rs._response_cache["t1"] = (time.monotonic() - rs._RESPONSE_TTL - 1, data)

    forced = await c.response(force=True)
    assert forced == {"v": 2}
    assert state["n"] == 2


async def test_non_force_recomputes_when_cache_stale():
    c = _consumer()
    state, c._compute_response = _counting_compute()

    await c.response()
    rs._response_cache["t1"] = (time.monotonic() - rs._RESPONSE_TTL - 1, {"v": 1})

    again = await c.response()
    assert state["n"] == 2
    assert again == {"v": 2}


async def test_get_latest_activity_broadcasts_and_schedules_trailing():
    c = _consumer()
    _state, c._compute_response = _counting_compute()
    c.reply = AsyncMock()
    c.subscribers = {"r1": {"action": "list_subscribe", "response": None}}

    await c.get_latest_activity({})

    c.reply.assert_awaited_once()  # изменение доставлено подписчику
    assert c.subscribers["r1"]["response"] == {"v": 1}
    assert c._trailing is not None and not c._trailing.done()

    c._cancel_trailing()


async def test_get_latest_activity_noop_without_subscribers():
    c = _consumer()
    c._compute_response = AsyncMock()
    c.reply = AsyncMock()

    await c.get_latest_activity({})

    c._compute_response.assert_not_called()
    c.reply.assert_not_awaited()
    assert c._trailing is None


async def test_broadcast_dedups_unchanged_response():
    c = _consumer()
    c.reply = AsyncMock()
    c.subscribers = {"r1": {"action": "a", "response": {"v": 1}}}

    await c._broadcast({"v": 1})  # то же значение — повторно не шлём

    c.reply.assert_not_awaited()


async def test_ensure_trailing_refresh_is_idempotent_while_pending():
    c = _consumer()

    async def _never():
        await asyncio.sleep(10)

    c._trailing_refresh = _never
    c._ensure_trailing_refresh()
    task1 = c._trailing
    c._ensure_trailing_refresh()  # уже висит — не плодим вторую задачу
    assert c._trailing is task1

    c._cancel_trailing()
    await asyncio.sleep(0)  # даём циклу обработать отмену (она кооперативная)
    assert task1.cancelled()


async def test_trailing_refresh_broadcasts_forced_response():
    c = _consumer()
    c._broadcast = AsyncMock()
    c.response = AsyncMock(return_value={"v": 9})
    c.subscribers = {"r1": {}}

    # Не ждём реальный TTL.
    real_sleep = asyncio.sleep

    async def _fast_sleep(_):
        await real_sleep(0)

    orig = asyncio.sleep
    asyncio.sleep = _fast_sleep
    try:
        await c._trailing_refresh()
    finally:
        asyncio.sleep = orig

    c.response.assert_awaited_once_with(force=True)
    c._broadcast.assert_awaited_once_with({"v": 9})


async def test_trailing_refresh_skips_when_no_subscribers():
    c = _consumer()
    c._broadcast = AsyncMock()
    c.response = AsyncMock()
    c.subscribers = {}

    orig = asyncio.sleep
    asyncio.sleep = lambda _: orig(0)
    try:
        await c._trailing_refresh()
    finally:
        asyncio.sleep = orig

    c.response.assert_not_awaited()
    c._broadcast.assert_not_awaited()


async def test_disconnect_cancels_trailing():
    c = _consumer()

    async def _never():
        await asyncio.sleep(10)

    c._trailing_refresh = _never
    c._ensure_trailing_refresh()
    task = c._trailing

    # Патчим родительский disconnect в MRO, чтобы не дёргать реальный канальный слой.
    parent = next(k for k in RoomStatusConsumer.__mro__[1:] if "disconnect" in k.__dict__)
    orig = parent.disconnect
    parent.disconnect = AsyncMock()
    try:
        await c.disconnect(1000)
    finally:
        parent.disconnect = orig

    await asyncio.sleep(0)  # отмена кооперативная — даём циклу её обработать
    assert task.cancelled()
    assert c._trailing is None

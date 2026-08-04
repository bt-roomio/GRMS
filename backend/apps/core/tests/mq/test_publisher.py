"""Unit tests for the serialized Publisher (async)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from core.management.mq.engine.publisher import Publisher


async def test_publish_sends_body_and_routing_key():
    channel = MagicMock()
    channel.default_exchange.publish = AsyncMock()
    pub = Publisher(channel)

    await pub.publish(b'{"a":1}', "fromGRMS")

    channel.default_exchange.publish.assert_awaited_once()
    args, kwargs = channel.default_exchange.publish.call_args
    assert kwargs["routing_key"] == "fromGRMS"
    assert args[0].body == b'{"a":1}'
    assert not pub._lock.locked()  # lock released after publish


async def test_publish_serializes_concurrent_calls():
    channel = MagicMock()
    order = []

    async def slow_publish(_message, routing_key):
        order.append(("start", routing_key))
        await asyncio.sleep(0.01)
        order.append(("end", routing_key))

    channel.default_exchange.publish = AsyncMock(side_effect=slow_publish)
    pub = Publisher(channel)

    await asyncio.gather(pub.publish(b"1", "a"), pub.publish(b"2", "b"))

    # With the lock, each publish fully completes before the next starts.
    assert order[0][0] == "start" and order[1][0] == "end"
    assert order[2][0] == "start" and order[3][0] == "end"

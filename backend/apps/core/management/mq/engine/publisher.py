"""Serialized publisher for RabbitMQ responses.

A single aio_pika channel is shared across every queue's accumulator, and
``_handle_other`` publishes from several coroutines via ``asyncio.gather``. An
aio_pika channel is not safe for concurrent ``publish`` (frame interleaving), so
this wrapper serializes publishes behind an ``asyncio.Lock``.
"""

import asyncio

import aio_pika


class Publisher:
    def __init__(self, channel: aio_pika.abc.AbstractChannel):
        self._channel = channel
        self._lock = asyncio.Lock()

    async def publish(self, body: bytes, routing_key: str):
        async with self._lock:
            await self._channel.default_exchange.publish(
                aio_pika.Message(body=body),
                routing_key=routing_key,
            )

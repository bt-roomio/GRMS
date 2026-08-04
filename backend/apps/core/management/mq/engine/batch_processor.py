"""Batch accumulation + acknowledgement for a single queue.

``BatchAccumulator`` owns the message buffer and its lifecycle: it collects
incoming AMQP messages into batches (flushing on ``batch_size`` or
``batch_timeout``), hands each batch to a :class:`BatchProcessor` for the actual
topic routing / handler dispatch, and then ack/nacks every message based on the
outcome the processor reports.

Buffering + ack (transport concerns) live here; parsing, device resolution and
handler dispatch (business concerns) live in
:mod:`core.management.mq.engine.processor`.
"""

import asyncio
import logging

import aio_pika

from core.management.mq.engine.processor import (
    STATUS_REQUEUE,
    STATUS_SUCCESS,
    BatchProcessor,
)

logger = logging.getLogger("core")


class BatchAccumulator:
    def __init__(self, queue_name: str, batch_size=50, batch_timeout=0.3, publisher=None):
        self.queue_name = queue_name
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.message_queue = asyncio.Queue()
        self.shutdown_event = asyncio.Event()
        self.processor = BatchProcessor(queue_name, publisher)

    async def add_message(self, message: aio_pika.IncomingMessage):
        """Add message to queue (called by consumer callback)"""
        await self.message_queue.put(message)

    async def _collect_batch(self) -> list:
        """Drain a batch: block for the first message, then keep filling until either
        ``batch_size`` is reached or ``batch_timeout`` elapses since that first message.

        Closing the batch as soon as the queue is momentarily empty (a bare
        ``get_nowait`` loop) looks cheap, but at realistic arrival rates the next
        message is a few tens of milliseconds away, so batches degrade to 1-2
        messages and every message ends up costing its own pair of downstream Celery
        tasks. Lingering for the remainder of the window is what makes ``batch_size``
        mean anything; under load the queue is never empty and the wait never happens.
        """
        try:
            first = await asyncio.wait_for(self.message_queue.get(), timeout=self.batch_timeout)
        except TimeoutError:
            return []

        batch = [first]
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.batch_timeout

        while len(batch) < self.batch_size:
            # Fast path: take everything already buffered without touching the clock.
            try:
                batch.append(self.message_queue.get_nowait())
                continue
            except asyncio.QueueEmpty:
                pass

            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                batch.append(await asyncio.wait_for(self.message_queue.get(), timeout=remaining))
            except TimeoutError:
                break

        return batch

    def _drain_remaining(self) -> list:
        """Non-blocking drain of everything still queued (used on shutdown)."""
        batch = []
        while True:
            try:
                batch.append(self.message_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return batch

    async def start_processor(self):
        """Background task: accumulate and process batches"""
        while not self.shutdown_event.is_set():
            try:
                batch = await self._collect_batch()
                if batch:
                    await self.process_batch(batch)
            except Exception:
                logger.exception("[%s] Batch processor error", self.queue_name)

        # Shutdown: process remaining messages
        batch = self._drain_remaining()
        if batch:
            await self.process_batch(batch)
            logger.info("[%s] Processed remaining %d messages on shutdown", self.queue_name, len(batch))

    async def process_batch(self, batch: list[aio_pika.IncomingMessage]):
        """Dispatch the batch to the processor, then ack/nack per outcome."""
        logger.debug("[%s] Processing batch: %d messages", self.queue_name, len(batch))
        message_status = await self.processor.process(batch)
        await self.acknowledge_messages(batch, message_status)

    async def acknowledge_messages(self, batch: list, message_status: dict):
        """Acknowledge messages based on processing status"""
        for message in batch:
            try:
                status = message_status.get(message.delivery_tag, STATUS_REQUEUE)

                if status == STATUS_SUCCESS:
                    await message.ack()
                elif status == STATUS_REQUEUE:
                    await message.nack(requeue=True)
                else:  # STATUS_NO_REQUEUE (validation errors)
                    await message.nack(requeue=False)

            except Exception:
                logger.exception("[%s] Failed to ack/nack message %s", self.queue_name, message.delivery_tag)

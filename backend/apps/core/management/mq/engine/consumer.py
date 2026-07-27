"""RabbitMQ connection lifecycle for the async MQ consumer.

``AsyncMQConsumer`` owns the robust connection, declares every queue, spins up a
``BatchAccumulator`` + consumer channel per queue, and coordinates graceful
shutdown on signal.
"""

import asyncio
import logging

import aio_pika

from core.management.mq.config import (
    AMQP_URL,
    BATCH_SIZE,
    BATCH_TIMEOUT,
    PREFETCH_COUNT,
    QUEUE_CONFIG,
    QUEUE_FROM_GRMS,
    RECONNECT_INTERVAL,
)
from core.management.mq.engine.batch_processor import BatchAccumulator
from core.management.mq.engine.publisher import Publisher

logger = logging.getLogger("core")


class AsyncMQConsumer:
    def __init__(self):
        self.accumulators = {}
        self.queue_tasks = []
        self.shutdown_event = asyncio.Event()
        self.publish_channel = None
        self.publisher = None

    async def start(self):
        """Main entry point - start all queue consumers"""
        connection = await aio_pika.connect_robust(
            AMQP_URL,
            reconnect_interval=RECONNECT_INTERVAL,
        )
        async with connection:
            # Declare queues
            channel = await connection.channel()
            for queue_name in QUEUE_CONFIG:
                await channel.declare_queue(queue_name, durable=True)
            await channel.declare_queue(QUEUE_FROM_GRMS, durable=True)
            logger.info("Queues declared successfully")

            # Create shared publish channel for responses (serialized via Publisher)
            self.publish_channel = await connection.channel()
            self.publisher = Publisher(self.publish_channel)

            # Start consumer task for each queue
            for queue_name in QUEUE_CONFIG:
                task = asyncio.create_task(self.consume_queue(connection, queue_name))
                self.queue_tasks.append(task)

            logger.info("Started consuming from %d queues", len(QUEUE_CONFIG))

            # Wait for shutdown signal
            await self.shutdown_event.wait()

            # Graceful shutdown
            await self.shutdown_gracefully()

    async def consume_queue(self, connection, queue_name: str):
        """Consumer for a single queue"""
        # Create BatchAccumulator for this queue
        accumulator = BatchAccumulator(queue_name, BATCH_SIZE, BATCH_TIMEOUT, self.publisher)
        self.accumulators[queue_name] = accumulator

        # Start batch processor
        processor_task = asyncio.create_task(accumulator.start_processor())

        # Create channel and consume
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=PREFETCH_COUNT)
        queue = await channel.declare_queue(queue_name, durable=True, passive=True)

        async def message_callback(message: aio_pika.IncomingMessage):
            """Add message to batch accumulator"""
            await accumulator.add_message(message)

        await queue.consume(message_callback, no_ack=False)
        logger.info("[%s] Started consuming with prefetch_count=%d", queue_name, PREFETCH_COUNT)

        # Keep task alive
        try:
            await self.shutdown_event.wait()
        finally:
            accumulator.shutdown_event.set()
            await processor_task

    async def shutdown_gracefully(self):
        """Shutdown all consumers and process remaining batches"""
        logger.info("Shutting down gracefully...")

        # Signal all accumulators to shutdown
        for accumulator in self.accumulators.values():
            accumulator.shutdown_event.set()

        # Wait for all tasks to complete
        await asyncio.gather(*self.queue_tasks, return_exceptions=True)

        logger.info("Shutdown complete")

    def handle_signal(self, signum, frame):
        """Signal handler for SIGTERM/SIGINT"""
        logger.info("Received signal %s", signum)
        asyncio.create_task(self.trigger_shutdown())

    async def trigger_shutdown(self):
        self.shutdown_event.set()

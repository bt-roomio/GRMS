"""Event-loop entry point for the async MQ consumer.

Wires OS signal handlers to the consumer's shutdown event and owns the
``asyncio.run`` lifecycle plus Redis cleanup. Django must already be configured
before this module is imported.
"""

import asyncio
import logging
import signal

from core.management.mq.engine.consumer import AsyncMQConsumer
from core.utils.redis_pool import async_redis as redis_client

logger = logging.getLogger("core")


async def main():
    consumer = AsyncMQConsumer()

    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: consumer.handle_signal(s, None))

    try:
        await consumer.start()
    finally:
        await redis_client.aclose()
        logger.info("Redis connection closed")


def run():
    """Configure noisy third-party loggers and run the consumer event loop."""
    logging.getLogger("aiormq").setLevel(logging.WARNING)
    logging.getLogger("aio_pika").setLevel(logging.WARNING)

    asyncio.run(main())

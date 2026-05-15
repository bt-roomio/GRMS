import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path

import django

# Add backend directory to Python path
backend_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Initialize Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# ruff: disable[E402]
import aio_pika
import redis.asyncio as aioredis
from asgiref.sync import sync_to_async
from django.conf import settings

from core.management.mq.attributes import sync_attributes_batch
from core.management.mq.device_cache import (
    _DEVICE_MEMORY_CACHE,
    _MEMORY_CACHE_TTL,
    DeviceType,
    _update_memory_cache,
)
from core.management.mq.get_device import get_sub_device
from core.management.mq.mq_metrics import mq_keys_processed_total, mq_messages_processed_total
from core.management.mq.rpc_message import handle_rpc
from core.management.mq.state_device import handle_connect_disconnect
from core.management.mq.state_device_batch_async import sync_state_device_batch_async
from core.management.mq.telemetry import sync_telemetry_batch
from core.utils.get_time import get_mil_sec
from main.models import Device
from shuttle.models import AttributeKv
from shuttle.utils.get_non_null_field import get_non_null_field

# ruff: enable[E402]


# Queue Names
QUEUE_TO_GRMS = "toGRMS"
QUEUE_FROM_GRMS = "fromGRMS"
QUEUE_DEVICE_ATTRS_REQUEST = "v1/devices/me/attributes/request"
QUEUE_GATEWAY_RPC = "v1/gateway/rpc"
QUEUE_GATEWAY_ATTRS_REQUEST = "v1/gateway/attributes/request"
QUEUE_ATTRIBUTES = "/attributes"
QUEUE_TELEMETRY = "/telemetry"

QUEUE_CONFIG = [
    QUEUE_TO_GRMS,
    QUEUE_DEVICE_ATTRS_REQUEST,
    QUEUE_GATEWAY_RPC,
    QUEUE_GATEWAY_ATTRS_REQUEST,
    QUEUE_ATTRIBUTES,
    QUEUE_TELEMETRY,
]

# Message Topics
TOPIC_TELEMETRY = "/telemetry"
TOPIC_ATTRIBUTES = "/attributes"
TOPIC_GATEWAY_CONNECT = "v1/gateway/connect"
TOPIC_GATEWAY_DISCONNECT = "v1/gateway/disconnect"
TOPIC_GATEWAY_ATTRIBUTES_REQUEST = "v1/gateway/attributes/request"
TOPIC_DEVICES_ATTRIBUTES_REQUEST = "v1/devices/me/attributes/request"
TOPIC_GATEWAY_RPC = "v1/gateway/rpc"

# Batch processing configuration
BATCH_SIZE = 200
BATCH_TIMEOUT = 0.1  # 100ms
PREFETCH_COUNT = 1000

RB_LOGIN = settings.RABBIT_LOGIN
RB_PASSWORD = settings.RABBIT_PASSWORD
RB_HOST = settings.RABBIT_HOST
RB_PORT = settings.RABBIT_PORT

logger = logging.getLogger("core")

# Redis async client
redis_client = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

# Cache configuration
EXPIRY_TIME = 600  # 10 minutes


async def get_device(device_id: str, tenant_id=None) -> DeviceType | None:
    """Get device with 2-tier caching: memory → Redis → database (async version)"""
    # Tier 1: Check in-memory cache (fastest, no network)
    current_time = get_mil_sec() // 1000  # seconds
    cache_entry = _DEVICE_MEMORY_CACHE.get(device_id)
    if cache_entry and (current_time - cache_entry["cached_at"]) < _MEMORY_CACHE_TTL:
        return cache_entry["data"]

    # Tier 2: Check Redis cache
    cache_key = f"prs_msg:device_cache:{device_id}"
    cached_device_raw = await redis_client.get(cache_key)
    cached_device = cached_device_raw.decode("utf-8") if isinstance(cached_device_raw, bytes) else None

    if cached_device:
        logger.debug("Device found in Redis cache: %s", device_id)
        data = json.loads(cached_device)
        _update_memory_cache(device_id, data)
        return data

    # Tier 3: Database lookup
    filters = {"id": device_id}
    if "&" in device_id:
        filters = {"name": device_id.split("&")[1], "tenant_id": tenant_id, "is_active": True}

    device = await Device.objects.filter(**filters).afirst()

    if not device:
        return None

    data: DeviceType = {
        "id": str(device.id),
        "name": device.name,
        "tenant_id": str(device.tenant_id),
        "device_profile_id": str(device.device_profile_id),
    }

    await redis_client.set(cache_key, json.dumps(data), ex=EXPIRY_TIME)
    logger.debug("Device cached from DB: %s", device_id)
    _update_memory_cache(device_id, data)

    return data


def _extract_keys(topic: str, data) -> list[str]:
    keys = []
    if topic.endswith("/telemetry"):
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict):
                    keys.extend(entry.get("values", {}).keys())
        elif isinstance(data, dict):
            for device_data in data.values():
                if isinstance(device_data, list):
                    for entry in device_data:
                        if isinstance(entry, dict):
                            keys.extend(entry.get("values", {}).keys())
    elif topic.endswith("/attributes"):
        if isinstance(data, dict):
            first_val = next(iter(data.values()), None)
            if isinstance(first_val, dict):
                for sub in data.values():
                    if isinstance(sub, dict):
                        keys.extend(sub.keys())
            else:
                keys.extend(data.keys())
    return list(set(keys))


async def validate_body(body: bytes):
    msg = json.loads(body)
    device = await get_device(msg.get("sourceDeviceUUID"))
    if not device:
        raise ValueError(f"Device not found: {msg.get('sourceDeviceUUID')}")
    return device, msg


# Wrap sync batch functions (thread_sensitive=False allows parallel execution in thread pool)
sync_telemetry_batch_async = sync_to_async(sync_telemetry_batch, thread_sensitive=False)
sync_attributes_batch_async = sync_to_async(sync_attributes_batch, thread_sensitive=False)
# sync_state_device_batch_async is already async, imported directly

# Wrap individual handlers
handle_rpc_async = sync_to_async(handle_rpc, thread_sensitive=False)
handle_connect_disconnect_async = sync_to_async(handle_connect_disconnect, thread_sensitive=False)

# Wrap helper functions for attribute request
get_sub_device_async = sync_to_async(get_sub_device, thread_sensitive=False)


async def get_attribute_response(device: DeviceType, data: dict, topic: str):
    """Get attribute response (async version of handle_attribute_request logic)"""

    def _get_attributes_sync():
        shared_keys = data.get("sharedKeys") or data.get("keys") or []
        keys = shared_keys.split(",") if isinstance(shared_keys, str) else shared_keys
        device_id = device.get("id")

        if "gateway" in topic:
            sub_device = get_sub_device(device, name=data.get("device"))
            attrs = AttributeKv.objects.filter(attribute_type=AttributeKv.SHARED_SCOPE, entity=sub_device.get("id"))
            attrs = attrs.filter(attribute_key__in=keys) if keys else attrs
            return {
                "targetDeviceUUID": str(device_id),
                "topic": topic.replace("/request", ""),
                "data": {
                    "device": sub_device.get("name"),
                    "data": {a.attribute_key: get_non_null_field(a)[1] for a in attrs},
                    "id": data.get("id"),
                },
            }
        else:
            attrs = AttributeKv.objects.filter(attribute_type=AttributeKv.SHARED_SCOPE, entity=device_id)
            attrs = attrs.filter(attribute_key__in=keys) if keys else attrs
            return {
                "targetDeviceUUID": str(device_id),
                "topic": topic.replace("request", "response"),
                "data": {a.attribute_key: get_non_null_field(a)[1] for a in attrs},
            }

    return await sync_to_async(_get_attributes_sync, thread_sensitive=False)()


async def handle_attribute_request_async(topic: str, device: DeviceType, data: dict, publish_channel):
    """Handle attribute request with async RabbitMQ response"""
    try:
        # Get attribute response
        response = await get_attribute_response(device, data, topic)

        # Send response via shared channel
        await publish_channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps(response).encode()),
            routing_key=QUEUE_FROM_GRMS,
        )
        logger.debug("Attribute response sent for device %s", device.get("id"))
    except Exception:
        logger.exception("Failed to send attribute response")
        raise


class BatchAccumulator:
    def __init__(self, queue_name: str, batch_size=50, batch_timeout=0.1, publish_channel=None):
        self.queue_name = queue_name
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.publish_channel = publish_channel
        self.message_queue = asyncio.Queue()
        self.shutdown_event = asyncio.Event()

    async def add_message(self, message: aio_pika.IncomingMessage):
        """Add message to queue (called by consumer callback)"""
        await self.message_queue.put(message)

    async def start_processor(self):
        """Background task: accumulate and process batches"""
        batch = []
        last_batch_time = asyncio.get_event_loop().time()

        while not self.shutdown_event.is_set():
            try:
                # Calculate remaining timeout
                elapsed = asyncio.get_event_loop().time() - last_batch_time
                timeout = max(0.01, self.batch_timeout - elapsed)

                # Wait for message with timeout
                try:
                    message = await asyncio.wait_for(self.message_queue.get(), timeout=timeout)
                    batch.append(message)
                except asyncio.TimeoutError:
                    pass

                # Check if should process batch
                current_time = asyncio.get_event_loop().time()
                should_process = len(batch) >= self.batch_size or (
                    batch and (current_time - last_batch_time) >= self.batch_timeout
                )

                if should_process:
                    await self.process_batch(batch)
                    batch = []
                    last_batch_time = current_time

            except Exception:
                logger.exception("[%s] Batch processor error", self.queue_name)

        # Shutdown: process remaining messages
        if batch:
            await self.process_batch(batch)
            logger.info("[%s] Processed remaining %d messages on shutdown", self.queue_name, len(batch))

    async def process_batch(self, batch: list[aio_pika.IncomingMessage]):
        """Process batch with per-message success/failure tracking"""
        logger.debug("[%s] Processing batch: %d messages", self.queue_name, len(batch))

        # Group messages by type
        telemetry_batch = []
        attributes_batch = []
        device_connect_batch = []
        other_messages = []
        message_status = {}  # {delivery_tag: 'success'|'failure_requeue'|'failure_no_requeue'}

        # Step 1: Validate and group messages
        for message in batch:
            try:
                device, msg = await validate_body(message.body)
                topic = msg.get("topic", "")
                data = msg.get("data")

                gateway_id = device.get("id", "unknown")
                mq_messages_processed_total.labels(gateway_id=gateway_id, topic=topic).inc()
                for key in _extract_keys(topic, data):
                    mq_keys_processed_total.labels(gateway_id=gateway_id, key=key).inc()

                if topic.endswith(TOPIC_TELEMETRY):
                    telemetry_batch.append((device, topic, data, message))
                elif topic.endswith(TOPIC_ATTRIBUTES):
                    attributes_batch.append((device, topic, data, message))
                elif topic in (TOPIC_GATEWAY_CONNECT, TOPIC_GATEWAY_DISCONNECT):
                    device_connect_batch.append((device, topic, data, message))
                else:
                    other_messages.append((device, topic, data, message))

            except Exception:
                logger.warning(
                    "[%s] Validation failed for message %s", self.queue_name, message.delivery_tag, exc_info=True
                )
                message_status[message.delivery_tag] = "failure_no_requeue"

        # Steps 2-4: Process telemetry, attributes, device states in parallel
        async def _run_telemetry():
            if not telemetry_batch:
                return
            try:
                await sync_telemetry_batch_async([(d, t, data) for d, t, data, _ in telemetry_batch])
                for _, _, _, msg in telemetry_batch:
                    message_status[msg.delivery_tag] = "success"
                logger.debug("[%s] Processed telemetry batch: %d messages", self.queue_name, len(telemetry_batch))
            except Exception:
                logger.exception("[%s] Telemetry batch failed", self.queue_name)
                for _, _, _, msg in telemetry_batch:
                    message_status[msg.delivery_tag] = "failure_requeue"

        async def _run_attributes():
            if not attributes_batch:
                return
            try:
                await sync_attributes_batch_async([(d, t, data) for d, t, data, _ in attributes_batch])
                for _, _, _, msg in attributes_batch:
                    message_status[msg.delivery_tag] = "success"
                logger.debug("[%s] Processed attributes batch: %d messages", self.queue_name, len(attributes_batch))
            except Exception:
                logger.exception("[%s] Attributes batch failed", self.queue_name)
                for _, _, _, msg in attributes_batch:
                    message_status[msg.delivery_tag] = "failure_requeue"

        async def _run_device_states():
            if not device_connect_batch:
                return
            try:
                await sync_state_device_batch_async([(d, t, data) for d, t, data, _ in device_connect_batch])
                for _, _, _, msg in device_connect_batch:
                    message_status[msg.delivery_tag] = "success"
                logger.debug(
                    "[%s] Processed device state batch: %d messages", self.queue_name, len(device_connect_batch)
                )
            except Exception:
                logger.exception("[%s] Device state batch failed", self.queue_name)
                for _, _, _, msg in device_connect_batch:
                    message_status[msg.delivery_tag] = "failure_requeue"

        await asyncio.gather(_run_telemetry(), _run_attributes(), _run_device_states())

        # Step 5: Process other messages concurrently
        async def _handle_other(device, topic, data, message):
            try:
                if topic.startswith(TOPIC_GATEWAY_ATTRIBUTES_REQUEST) or topic.startswith(
                    TOPIC_DEVICES_ATTRIBUTES_REQUEST
                ):
                    await handle_attribute_request_async(topic, device, data, self.publish_channel)
                elif topic == TOPIC_GATEWAY_RPC:
                    await handle_rpc_async(data)
                else:
                    logger.warning("[%s] Unhandled topic: %s", self.queue_name, topic)
                message_status[message.delivery_tag] = "success"
            except Exception:
                logger.exception("[%s] Individual message processing failed", self.queue_name)
                message_status[message.delivery_tag] = "failure_requeue"

        if other_messages:
            await asyncio.gather(*[_handle_other(d, t, data, msg) for d, t, data, msg in other_messages])

        # Step 6: Acknowledge messages
        await self.acknowledge_messages(batch, message_status)

    async def acknowledge_messages(self, batch: list, message_status: dict):
        """Acknowledge messages based on processing status"""
        for message in batch:
            try:
                status = message_status.get(message.delivery_tag, "failure_requeue")

                if status == "success":
                    await message.ack()
                elif status == "failure_requeue":
                    await message.nack(requeue=True)
                else:  # failure_no_requeue (validation errors)
                    await message.nack(requeue=False)

            except Exception:
                logger.exception("[%s] Failed to ack/nack message %s", self.queue_name, message.delivery_tag)


class AsyncMQConsumer:
    def __init__(self):
        self.accumulators = {}  # {queue_name: BatchAccumulator}
        self.queue_tasks = []
        self.shutdown_event = asyncio.Event()
        self.publish_channel = None

    async def start(self):
        """Main entry point - start all queue consumers"""
        connection = await aio_pika.connect_robust(
            f"amqp://{RB_LOGIN}:{RB_PASSWORD}@{RB_HOST}:{RB_PORT}/",
            reconnect_interval=5,
        )
        async with connection:
            # Declare queues
            channel = await connection.channel()
            for queue_name in QUEUE_CONFIG:
                await channel.declare_queue(queue_name, durable=True)
            await channel.declare_queue(QUEUE_FROM_GRMS, durable=True)
            logger.info("Queues declared successfully")

            # Create shared publish channel for responses
            self.publish_channel = await connection.channel()

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
        accumulator = BatchAccumulator(queue_name, BATCH_SIZE, BATCH_TIMEOUT, self.publish_channel)
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


if __name__ == "__main__":
    logging.getLogger("aiormq").setLevel(logging.WARNING)
    logging.getLogger("aio_pika").setLevel(logging.WARNING)

    asyncio.run(main())

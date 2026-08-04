"""Batch processing / topic dispatch for the async MQ consumer.

``BatchProcessor`` has a single responsibility: turn a raw list of AMQP messages
into a per-message processing outcome. It parses bodies, resolves every source
device in one batch, routes messages to the right handler by topic (batched
handlers for telemetry/attributes/device-state, per-message handlers for the
rest) and reports ``{delivery_tag: status}``.

Buffering, batch timing and ack/nack are *not* here — they live in
:class:`core.management.mq.engine.batch_processor.BatchAccumulator`.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field

import aio_pika
import orjson

from core.management.mq.config import (
    TOPIC_ATTRIBUTES,
    TOPIC_DEVICES_ATTRIBUTES_REQUEST,
    TOPIC_GATEWAY_ATTRIBUTES_REQUEST,
    TOPIC_GATEWAY_CONNECT,
    TOPIC_GATEWAY_DISCONNECT,
    TOPIC_GATEWAY_RPC,
    TOPIC_TELEMETRY,
)
from core.management.mq.devices.device_resolver import resolve_devices_batch
from core.management.mq.engine.validation import _extract_keys
from core.management.mq.engine.wrappers import (
    handle_rpc_async,
    sync_attributes_batch_async,
    sync_telemetry_batch_async,
)
from core.management.mq.handlers.attribute_request import handle_attribute_request_async
from core.management.mq.handlers.state_device_batch_async import sync_state_device_batch_async
from core.management.mq.mq_metrics import mq_keys_processed_total, mq_messages_processed_total

logger = logging.getLogger("core")

# Per-message processing outcome, keyed by delivery_tag.
STATUS_SUCCESS = "success"
STATUS_REQUEUE = "failure_requeue"
STATUS_NO_REQUEUE = "failure_no_requeue"

# One routed entry: (device, topic, data, message)
RoutedMessage = tuple[dict, str, object, aio_pika.IncomingMessage]


@dataclass
class RoutedBatch:
    """Messages grouped by the handler they will be dispatched to."""

    telemetry: list[RoutedMessage] = field(default_factory=list)
    attributes: list[RoutedMessage] = field(default_factory=list)
    device_connect: list[RoutedMessage] = field(default_factory=list)
    other: list[RoutedMessage] = field(default_factory=list)


class BatchProcessor:
    def __init__(self, queue_name: str, publisher=None):
        self.queue_name = queue_name
        self.publisher = publisher

    async def process(self, batch: list[aio_pika.IncomingMessage]) -> dict:
        """Process a batch and return ``{delivery_tag: status}`` for every message."""
        message_status: dict = {}

        parsed, source_ids = self._parse(batch, message_status)
        device_map = await resolve_devices_batch(source_ids) if source_ids else {}
        grouped = self._route(parsed, device_map, message_status)

        # Telemetry, attributes and device states are independent — run in parallel.
        await asyncio.gather(
            self._run_group("Telemetry", grouped.telemetry, sync_telemetry_batch_async, message_status),
            self._run_group("Attributes", grouped.attributes, sync_attributes_batch_async, message_status),
            self._run_group("Device state", grouped.device_connect, sync_state_device_batch_async, message_status),
        )

        if grouped.other:
            await asyncio.gather(*(self._handle_other(entry, message_status) for entry in grouped.other))

        return message_status

    def _parse(self, batch, message_status: dict):
        """Parse message bodies; collect (message, msg) pairs and the set of source ids."""
        parsed = []
        source_ids: set = set()
        for message in batch:
            try:
                msg = orjson.loads(message.body)
                logger.debug("Message: %s", str(msg))
            except Exception as exc:
                logger.warning("[%s] Failed to parse message %s", self.queue_name, message.delivery_tag, exc_info=exc)
                message_status[message.delivery_tag] = STATUS_NO_REQUEUE
                continue
            parsed.append((message, msg))
            source_id = msg.get("sourceDeviceUUID")
            if source_id:
                source_ids.add(source_id)
        return parsed, source_ids

    def _route(self, parsed, device_map: dict, message_status: dict) -> RoutedBatch:
        """Group parsed messages by topic, emit metrics, and mark unknown devices."""
        grouped = RoutedBatch()
        # Аккумулируем счётчики по батчу: один label-lookup на топик (их немного)
        # вместо одного на каждое сообщение, и без серии на каждый gateway_id
        # (эта метка убрана, чтобы не плодить кардинальность).
        topic_counts: dict[str, int] = defaultdict(int)
        key_count = 0
        for message, msg in parsed:
            device = device_map.get(msg.get("sourceDeviceUUID"))
            if not device:
                logger.warning("[%s] Device not found: %s", self.queue_name, msg.get("sourceDeviceUUID"))
                message_status[message.delivery_tag] = STATUS_NO_REQUEUE
                continue

            topic = msg.get("topic", "")
            data = msg.get("data")

            topic_counts[topic] += 1
            key_count += len(_extract_keys(topic, data))

            entry = (device, topic, data, message)
            if topic.endswith(TOPIC_TELEMETRY):
                grouped.telemetry.append(entry)
            elif topic.endswith(TOPIC_ATTRIBUTES):
                grouped.attributes.append(entry)
            elif topic in (TOPIC_GATEWAY_CONNECT, TOPIC_GATEWAY_DISCONNECT):
                grouped.device_connect.append(entry)
            else:
                grouped.other.append(entry)

        for topic, count in topic_counts.items():
            mq_messages_processed_total.labels(topic=topic).inc(count)
        if key_count:
            mq_keys_processed_total.inc(key_count)
        return grouped

    async def _run_group(self, label: str, items: list, handler, message_status: dict):
        """Run one batched handler and mark every message in the group success/requeue."""
        if not items:
            return
        try:
            await handler([(device, topic, data) for device, topic, data, _ in items])
            for *_, message in items:
                message_status[message.delivery_tag] = STATUS_SUCCESS
            logger.debug("[%s] Processed %s batch: %d messages", self.queue_name, label.lower(), len(items))
        except Exception:
            logger.exception("[%s] %s batch failed", self.queue_name, label)
            for *_, message in items:
                message_status[message.delivery_tag] = STATUS_REQUEUE

    async def _handle_other(self, entry: RoutedMessage, message_status: dict):
        """Dispatch a single non-batched message (attribute request / RPC)."""
        device, topic, data, message = entry
        try:
            if topic.startswith(TOPIC_GATEWAY_ATTRIBUTES_REQUEST) or topic.startswith(TOPIC_DEVICES_ATTRIBUTES_REQUEST):
                await handle_attribute_request_async(topic, device, data, self.publisher)  # ty: ignore
            elif topic == TOPIC_GATEWAY_RPC:
                await handle_rpc_async(data)
            else:
                logger.warning("[%s] Unhandled topic: %s", self.queue_name, topic)
            message_status[message.delivery_tag] = STATUS_SUCCESS
        except Exception:
            logger.exception("[%s] Individual message processing failed", self.queue_name)
            message_status[message.delivery_tag] = STATUS_REQUEUE

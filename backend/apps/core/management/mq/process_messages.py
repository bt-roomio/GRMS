import json
import logging

import pika
import redis
from django.conf import settings
from pika.adapters.blocking_connection import BlockingChannel

from core.management.mq.attribute_kv import handle_attribute_request
from core.management.mq.attributes import sync_attributes, sync_attributes_batch
from core.management.mq.get_device import get_device
from core.management.mq.rpc_message import handle_rpc
from core.management.mq.state_device import handle_connect_disconnect
from core.management.mq.telemetry import sync_telemetry, sync_telemetry_batch

redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

logger = logging.getLogger(__name__)

logger_pika = logging.getLogger("pika")
logger_pika.setLevel(logging.WARNING)


def process_messages(ch: BlockingChannel, method: pika.spec.Basic.Deliver, body: bytes):
    logger.debug("Received message: %s", body)
    device, msg = validate_body(body)
    topic = msg.get("topic", "")
    data = msg.get("data")

    if topic.startswith("v1/gateway/attributes/request") or topic.startswith("v1/devices/me/attributes/request"):
        handle_attribute_request(ch, topic, device, data)  # pyright:ignore
    elif topic == "v1/gateway/rpc":
        handle_rpc(data)
    elif topic in ("v1/gateway/connect", "v1/gateway/disconnect"):
        handle_connect_disconnect(device, topic, data)
    elif topic.endswith("/telemetry"):
        sync_telemetry(device, topic, data)
    elif topic.endswith("/attributes"):
        sync_attributes(device, topic, data)
    else:
        logger.warning("Unhandled topic: %s", topic)


def validate_body(body: bytes):
    msg = json.loads(body)
    device = get_device(msg.get("sourceDeviceUUID"))
    if not device:
        raise ValueError("Device not found: %s", msg.get("sourceDeviceUUID"))
    return device, msg


def process_messages_batch(ch: BlockingChannel, bodies: list[bytes]):
    """Process a batch of messages, grouping by type for bulk operations"""
    logger.debug("Processing batch of %d messages", len(bodies))

    # Group messages by type
    telemetry_batch = []
    attributes_batch = []
    other_messages = []  # For non-batchable types (RPC, connect/disconnect, attribute requests)

    for body in bodies:
        try:
            device, msg = validate_body(body)
            topic = msg.get("topic", "")
            data = msg.get("data")

            if topic.endswith("/telemetry"):
                telemetry_batch.append((device, topic, data))
            elif topic.endswith("/attributes"):
                attributes_batch.append((device, topic, data))
            else:
                # Non-batchable message types - process individually
                other_messages.append((ch, device, topic, data))

        except Exception as e:
            logger.warning("Failed to parse message in batch: %s", e)
            continue

    # Process batched telemetry
    if telemetry_batch:
        try:
            sync_telemetry_batch(telemetry_batch)
            logger.debug("Processed telemetry batch: %d messages", len(telemetry_batch))
        except Exception as e:
            logger.exception("Failed to process telemetry batch: %s", e)

    # Process batched attributes
    if attributes_batch:
        try:
            sync_attributes_batch(attributes_batch)
            logger.debug("Processed attributes batch: %d messages", len(attributes_batch))
        except Exception as e:
            logger.exception("Failed to process attributes batch: %s", e)

    # Process other messages individually
    for ch, device, topic, data in other_messages:
        try:
            if topic.startswith("v1/gateway/attributes/request") or topic.startswith(
                "v1/devices/me/attributes/request"
            ):
                handle_attribute_request(ch, topic, device, data)
            elif topic == "v1/gateway/rpc":
                handle_rpc(data)
            elif topic in ("v1/gateway/connect", "v1/gateway/disconnect"):
                handle_connect_disconnect(device, topic, data)
            else:
                logger.warning("Unhandled topic: %s", topic)
        except Exception as e:
            logger.warning("Failed to process individual message in batch: %s", e)

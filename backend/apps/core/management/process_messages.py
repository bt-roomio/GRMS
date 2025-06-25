import json
import logging
import time

import pika
import redis
from django.conf import settings
from pika.adapters.blocking_connection import BlockingChannel

from core.management.mq.attribute_kv import handle_attribute_request
from core.management.mq.attributes import sync_attributes
from core.management.mq.get_device import get_device
from core.management.mq.rpc_message import handle_rpc
from core.management.mq.state_device import handle_connect_disconnect
from core.management.mq.telemetry import sync_telemetry

redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logger_pika = logging.getLogger("pika")
logger_pika.setLevel(logging.WARNING)

EXPIRY_TIME = 60


def validate_body(body: bytes):
    msg = json.loads(body)

    device = get_device(msg.get("sourceDeviceUUID"))
    if not device:
        logger.warning("Device not found: %s", msg.get("sourceDeviceUUID"))
        raise ValueError("Device not found")
    return device, msg


def process_messages(ch: BlockingChannel, method: pika.spec.Basic.Deliver, body: bytes):
    logger.info("Received message: %s", body)
    device, msg = validate_body(body)
    topic = msg.get("topic", "")
    data = msg.get("data")
    logger.debug(str(f"{msg}, {device}"))

    device_id = device.get("id")

    if topic.startswith("v1/gateway/attributes/request") or topic.startswith("v1/devices/me/attributes/request"):
        logger.debug("Scheduling attribute response task for device %s topic %s", device_id, topic)
        handle_attribute_request(ch, device_id, topic, data)  # pyright:ignore
    elif topic == "v1/gateway/rpc":
        handle_rpc(data)
    elif topic in ("v1/gateway/connect", "v1/gateway/disconnect"):
        handle_connect_disconnect(device, topic, data)
    elif topic.endswith("/telemetry"):
        start_time = time.time()
        sync_telemetry(device, topic, data)
        logger.info(f"Synced telemetry for device {device_id} in {time.time() - start_time} seconds")
    elif topic.endswith("/attributes"):
        start_time = time.time()
        sync_attributes(device, topic, data)
        logger.info(f"Synced attributes for device {device_id} in {time.time() - start_time} seconds")
    else:
        logger.debug("Unhandled topic: %s", topic)

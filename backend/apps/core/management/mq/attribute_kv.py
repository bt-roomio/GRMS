import logging
from typing import TypedDict

from core.management.mq.get_device import DeviceType, get_sub_device
from core.rabbitmq.config import send_to_rabbitmq
from shuttle.models import AttributeKv
from shuttle.utils.get_non_null_field import get_non_null_field

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class AttributeRequestType(TypedDict):
    sharedKeys: str
    keys: str
    device: str
    client: bool
    id: int


def handle_attribute_request(ch, topic: str, device: DeviceType, data: AttributeRequestType):
    logger.debug("handle_attribute_request: device=%s topic=%s", device["id"], topic)
    try:
        device_id = device.get("id")
        sub_device_id = None
        if "gateway" in topic:
            sub_device = get_sub_device(device, name=data.get("device"))
            sub_device_id = sub_device.get("id")

        print(f"{sub_device_id or device_id}")
        shared_keys = data.get("sharedKeys") or data.get("keys") or []
        keys = shared_keys.split(",") if isinstance(shared_keys, str) else shared_keys
        attrs = AttributeKv.objects.filter(attribute_type=AttributeKv.SHARED_SCOPE, entity=sub_device_id or device_id)
        attrs = attrs.filter(attribute_key__in=keys) if keys else attrs
        response = {
            "targetDeviceUUID": str(device_id),
            "topic": topic.replace("request", "response"),
            "data": {a.attribute_key: get_non_null_field(a)[1] for a in attrs},
        }
        send_to_rabbitmq(ch, response, routing_key="fromGRMS")
        logger.debug("Attribute response sent for device %s %s", device_id, response)
    except Exception as exc:
        logger.exception("Failed to send attribute response: %s", exc)
        raise

import logging

from core.rabbitmq.config import send_to_rabbitmq
from shuttle.models import AttributeKv
from shuttle.utils.get_non_null_field import get_non_null_field

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def handle_attribute_request(ch, device_id: str, topic: str, data: dict):
    logger.debug("handle_attribute_request: device=%s topic=%s", device_id, topic)
    try:
        shared_keys = data.get("sharedKeys") or data.get("keys") or []
        keys = shared_keys.split(",") if isinstance(shared_keys, str) else shared_keys
        attrs = AttributeKv.objects.filter(attribute_type=AttributeKv.SHARED_SCOPE, entity=device_id)
        attrs = attrs.filter(attribute_key__in=keys) if keys else attrs
        response = {
            "targetDeviceUUID": str(device_id),
            "topic": topic.replace("request", "response"),
            "data": {a.attribute_key: get_non_null_field(a)[1] for a in attrs},
        }
        send_to_rabbitmq(ch, response, routing_key="fromGRMS")
        logger.debug("Attribute response sent for device %s", device_id)
    except Exception as exc:
        logger.exception("Failed to send attribute response: %s", exc)
        raise

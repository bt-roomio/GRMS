"""Attribute-request handling for the MQ consumer.

Builds the shared-scope attribute response for device/gateway
``.../attributes/request`` topics and publishes it back to ``fromGRMS``.
"""

import logging

import orjson
from asgiref.sync import sync_to_async

from core.management.mq.config import QUEUE_FROM_GRMS
from core.management.mq.db_safe import _db_safe
from core.management.mq.devices.device_cache import DeviceType
from core.management.mq.devices.get_device import get_sub_device
from shuttle.models import AttributeKv
from shuttle.utils.get_non_null_field import get_non_null_field

logger = logging.getLogger("core")


async def get_attribute_response(device: DeviceType, data: dict, topic: str):
    """Get attribute response (async version of handle_attribute_request logic)"""

    def _get_attributes_sync():
        shared_keys = data.get("sharedKeys") or data.get("keys") or []
        keys = shared_keys.split(",") if isinstance(shared_keys, str) else shared_keys
        device_id = device.get("id")

        if "gateway" in topic:
            sub_device = get_sub_device(device, name=data.get("device"))
            attrs = AttributeKv.objects.filter(
                attribute_type=AttributeKv.SHARED_SCOPE, entity=sub_device.get("id")
            ).order_by()
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
            attrs = AttributeKv.objects.filter(attribute_type=AttributeKv.SHARED_SCOPE, entity=device_id).order_by()
            attrs = attrs.filter(attribute_key__in=keys) if keys else attrs
            return {
                "targetDeviceUUID": str(device_id),
                "topic": topic.replace("request", "response"),
                "data": {a.attribute_key: get_non_null_field(a)[1] for a in attrs},
            }

    return await sync_to_async(_db_safe(_get_attributes_sync), thread_sensitive=False)()


async def handle_attribute_request_async(topic: str, device: DeviceType, data: dict, publisher):
    """Handle attribute request with async RabbitMQ response"""
    try:
        # Get attribute response
        response = await get_attribute_response(device, data, topic)

        # Send response via the serialized publisher (shared channel, locked)
        await publisher.publish(orjson.dumps(response), QUEUE_FROM_GRMS)
        logger.debug("Attribute response sent for device %s", device.get("id"))
    except Exception:
        logger.exception("Failed to send attribute response")
        raise

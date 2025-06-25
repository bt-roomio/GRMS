import logging
from collections import defaultdict

import redis
from django.conf import settings

from core.management.mq.get_device import get_sub_device
from core.management.mq.state_device import update_activity_device
from core.utils.get_time import get_mil_sec
from shuttle.models import AttributeKv
from shuttle.services.attribute_kv import publish_updates_attribute_batch
from shuttle.utils.find_compatible_field import find_compatible_field

redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

EXPIRY_TIME = 3600


def sync_attributes(device, topic, payload):
    device_id = device.get("id")
    logger.debug("Sync attributes: device=%s topic=%s", device_id, topic)
    if topic.startswith("v1/gateway/") and isinstance(payload, dict) and not topic.endswith("request"):
        for sub_name, attrs in payload.items():
            sub_device = get_sub_device(device, name=sub_name)
            _update_attribute_store(sub_device, attrs)
    else:
        _update_attribute_store(device, payload)


def _update_attribute_store(device, data):
    """
    Bulk save attributes for the given device using bulk_create and bulk_update.
    """
    device_id = device.get("id")
    entries = data if isinstance(data, list) else [data]
    ts_now = get_mil_sec()
    updates = []

    for entry in entries:
        for key, (field, value) in find_compatible_field(entry).items():
            updates.append((key, field, value))
    if not updates:
        logger.debug("No attribute entries to save for device %s", device_id)
        update_activity_device(device)
        return

    # Determine unique keys
    keys = list({u[0] for u in updates})
    # Fetch existing AttributeKv rows
    existing_qs = AttributeKv.objects.filter(
        entity_id=device_id,
        attribute_type=AttributeKv.CLIENT_SCOPE,
        attribute_key__in=keys,
    )
    existing_map = {obj.attribute_key: obj for obj in existing_qs}

    to_create = []
    to_update = []
    for key, field, value in updates:
        # Prepare default values
        base = {
            "bool_v": None,
            "str_v": None,
            "long_v": None,
            "dbl_v": None,
            "json_v": None,
            "entity_type": "DEVICE",
            "last_update_ts": ts_now,
            field: value,
        }
        if key in existing_map:
            inst = existing_map[key]
            for attr_name, attr_val in base.items():
                setattr(inst, attr_name, attr_val)
            to_update.append(inst)
        else:
            inst = AttributeKv(
                entity_id=device_id,
                attribute_type=AttributeKv.CLIENT_SCOPE,
                attribute_key=key,
                **base,
            )
            to_create.append(inst)

    # Bulk operations
    if to_create:
        AttributeKv.objects.bulk_create(to_create)
    if to_update:
        fields = ["bool_v", "str_v", "long_v", "dbl_v", "json_v", "last_update_ts", "entity_type"]
        AttributeKv.objects.bulk_update(to_update, fields)

    # Prepare updates for WebSocket clients
    updates_by_device = defaultdict(list)
    for attr in to_create + to_update:
        updates_by_device[device_id].append(
            {
                "entity": str(device_id),
                "key_name": attr.attribute_key,
                "last_update_ts": ts_now,
                "scope": AttributeKv.CLIENT_SCOPE,
                "bool_v": attr.bool_v,
                "str_v": attr.str_v,
                "long_v": attr.long_v,
                "dbl_v": attr.dbl_v,
                "json_v": attr.json_v,
            }
        )

    # Send updates to WebSocket clients
    if updates_by_device:
        publish_updates_attribute_batch(updates_by_device)

    logger.debug(
        "Bulk attributes processed for device %s: created=%d updated=%d", device_id, len(to_create), len(to_update)
    )
    update_activity_device(device_id)

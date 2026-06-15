import logging
from collections import defaultdict

import redis
from django.conf import settings

from core.management.mq.get_device import get_sub_device
from core.management.mq.state_device import update_activity_device
from core.utils.get_time import get_mil_sec
from shuttle.models import AttributeKv
from shuttle.tasks import (
    publish_updates_attribute_batch_task,
    update_activity_device_task,
    update_activity_devices_batch_task,
)
from shuttle.utils.find_compatible_field import find_compatible_field

redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# Increased cache TTL from 3600s (1h) to 7200s (2h) for consistency with telemetry.py
EXPIRY_TIME = 7200


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
        update_activity_device_task.delay(device_id)
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
        # ignore_conflicts prevents errors when concurrent updates create duplicates
        AttributeKv.objects.bulk_create(to_create, ignore_conflicts=True)
    if to_update:
        fields = ["bool_v", "str_v", "long_v", "dbl_v", "json_v", "last_update_ts", "entity_type"]
        AttributeKv.objects.bulk_update(to_update, fields)

    # Prepare updates for WebSocket clients
    updates_by_device = defaultdict(list)
    fields = ["bool_v", "str_v", "dbl_v", "long_v", "json_v"]
    for attr in to_create + to_update:
        updates_by_device[f"{device_id}_{device.get('tenant_id')}"].append(
            {
                "entity": str(device_id),
                "key_name": attr.attribute_key,
                "last_update_ts": ts_now,
                "scope": AttributeKv.CLIENT_SCOPE,
                "value": next((getattr(attr, field) for field in fields if getattr(attr, field) is not None), None),
            }
        )

    # Send updates to WebSocket clients asynchronously via Celery
    # This prevents blocking the RabbitMQ worker on WebSocket operations
    if updates_by_device:
        publish_updates_attribute_batch_task.delay(updates_by_device)

    logger.debug(
        "Bulk attributes processed for device %s: created=%d updated=%d", device_id, len(to_create), len(to_update)
    )
    update_activity_device(device_id)


def sync_attributes_batch(batch: list[tuple]):
    """
    Process multiple attribute messages in a single batch.
    batch: list of (device, topic, data) tuples
    """
    # Collect all device updates
    device_updates = defaultdict(list)  # {device_id: [(key, field, value), ...]}
    device_info = {}  # {device_id: device}

    for device, topic, payload in batch:
        if topic.startswith("v1/gateway/") and isinstance(payload, dict) and not topic.endswith("request"):
            for sub_name, attrs in payload.items():
                sub_device = get_sub_device(device, name=sub_name)
                sub_device_id = sub_device.get("id")
                device_info[sub_device_id] = sub_device
                _collect_attribute_updates(sub_device_id, attrs, device_updates)
        else:
            device_id = device.get("id")
            device_info[device_id] = device
            _collect_attribute_updates(device_id, payload, device_updates)

    if not device_updates:
        logger.debug("No attribute updates in batch")
        return

    # Process all updates in a single batch
    _update_attribute_store_batch(device_updates, device_info)


def _collect_attribute_updates(device_id, data, device_updates):
    """Collect attribute updates for a device"""
    entries = data if isinstance(data, list) else [data]
    for entry in entries:
        for key, (field, value) in find_compatible_field(entry).items():
            device_updates[device_id].append((key, field, value))


def _update_attribute_store_batch(device_updates, device_info):
    """
    Bulk save attributes for multiple devices using a single INSERT ... ON CONFLICT DO UPDATE.
    device_updates: {device_id: [(key, field, value), ...]}
    device_info: {device_id: device}
    """
    logger.debug("Starting batch attribute update for %d devices", len(device_updates))
    ts_now = get_mil_sec()

    all_objects = []
    updates_by_device = defaultdict(list)

    for device_id, updates in device_updates.items():
        device = device_info.get(device_id)
        if not device:
            continue

        # Last write wins for duplicate (device_id, key) within the same batch
        deduped = {key: (field, value) for key, field, value in updates}

        for key, (field, value) in deduped.items():
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
            all_objects.append(
                AttributeKv(
                    entity_id=device_id,
                    attribute_type=AttributeKv.CLIENT_SCOPE,
                    attribute_key=key,
                    **base,
                )
            )
            updates_by_device[f"{device_id}_{device.get('tenant_id')}"].append(
                {
                    "entity": str(device_id),
                    "key_name": key,
                    "last_update_ts": ts_now,
                    "scope": AttributeKv.CLIENT_SCOPE,
                    "value": value,
                }
            )

    if not all_objects:
        logger.debug("No attribute updates in batch")
        return

    # Single upsert matching the DB constraint: unique_attrkv_type_scope_entity_key
    AttributeKv.objects.bulk_create(
        all_objects,
        update_conflicts=True,
        update_fields=["bool_v", "str_v", "long_v", "dbl_v", "json_v", "last_update_ts"],
        unique_fields=["entity_type", "attribute_type", "entity_id", "attribute_key"],
    )

    # Mirror scanned_devices CLIENT_SCOPE → SHARED_SCOPE in a single bulk upsert
    scanned = [attr for attr in all_objects if attr.attribute_key == "scanned_devices"]
    if scanned:
        AttributeKv.objects.bulk_create(
            [
                AttributeKv(
                    attribute_key="scanned_devices",
                    attribute_type=AttributeKv.SHARED_SCOPE,
                    entity_id=attr.entity_id,
                    json_v=attr.json_v,
                    entity_type="DEVICE",
                    last_update_ts=ts_now,
                )
                for attr in scanned
            ],
            update_conflicts=True,
            update_fields=["json_v", "last_update_ts"],
            unique_fields=["entity_type", "attribute_type", "entity_id", "attribute_key"],
        )

    # Offload WebSocket publish to Celery — avoids async_to_sync inside thread pool worker
    if updates_by_device:
        publish_updates_attribute_batch_task.delay(dict(updates_by_device))

    # One Celery task for all devices instead of N separate dispatches
    update_activity_devices_batch_task.delay(list(device_updates.keys()))

    logger.debug("Batch attributes processed: %d devices, %d objects", len(device_updates), len(all_objects))

import logging
import random
import time
from collections import defaultdict

from django.db import OperationalError

from core.management.mq.devices.get_device import get_sub_device
from core.utils.get_time import get_mil_sec
from shuttle.models import AttributeKv
from shuttle.tasks import (
    publish_updates_attribute_batch_task,
    update_activity_devices_batch_task,
)
from shuttle.utils.find_compatible_field import find_compatible_field

logger = logging.getLogger(__name__)

# Increased cache TTL from 3600s (1h) to 7200s (2h) for consistency with telemetry.py
EXPIRY_TIME = 7200

_MAX_DEADLOCK_RETRIES = 3


def _bulk_upsert(objects, update_fields, unique_fields):
    """INSERT ... ON CONFLICT DO UPDATE with exponential-backoff retry on deadlock."""
    for attempt in range(_MAX_DEADLOCK_RETRIES):
        try:
            AttributeKv.objects.bulk_create(
                objects,
                update_conflicts=True,
                update_fields=update_fields,
                unique_fields=unique_fields,
            )
            return
        except OperationalError as exc:
            if "deadlock" in str(exc).lower() and attempt < _MAX_DEADLOCK_RETRIES - 1:
                time.sleep(0.05 * (2**attempt) + random.uniform(0, 0.02))
            else:
                raise


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

    # Sort by unique constraint fields so concurrent instances always acquire index locks
    # in the same order, preventing circular waits (deadlocks) between mq-async replicas.
    all_objects.sort(key=lambda x: (x.entity_type, x.attribute_type, str(x.entity_id), x.attribute_key))

    _bulk_upsert(
        all_objects,
        update_fields=["bool_v", "str_v", "long_v", "dbl_v", "json_v", "last_update_ts"],
        unique_fields=["entity_type", "attribute_type", "entity_id", "attribute_key"],
    )

    # Mirror scanned_devices CLIENT_SCOPE → SHARED_SCOPE in a single bulk upsert
    scanned = [attr for attr in all_objects if attr.attribute_key == "scanned_devices"]
    if scanned:
        scanned_mirror = [
            AttributeKv(
                attribute_key="scanned_devices",
                attribute_type=AttributeKv.SHARED_SCOPE,
                entity_id=attr.entity_id,
                json_v=attr.json_v,
                entity_type="DEVICE",
            )
            for attr in scanned
        ]
        scanned_mirror.sort(key=lambda x: str(x.entity_id))
        _bulk_upsert(
            scanned_mirror,
            update_fields=["json_v"],
            unique_fields=["entity_type", "attribute_type", "entity_id", "attribute_key"],
        )

    # Offload WebSocket publish to Celery — avoids async_to_sync inside thread pool worker
    if updates_by_device:
        publish_updates_attribute_batch_task.delay(dict(updates_by_device))

    # One Celery task for all devices instead of N separate dispatches
    update_activity_devices_batch_task.delay(list(device_updates.keys()))

    logger.debug("Batch attributes processed: %d devices, %d objects", len(device_updates), len(all_objects))

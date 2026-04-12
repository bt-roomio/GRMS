import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import DefaultDict

import redis
from access_manager.models import CardLog
from django.conf import settings

from core.management.mq.get_device import get_sub_device
from core.management.mq.handle_fias import handle_fias
from core.utils.date import unix_to_datetime
from core.utils.get_time import get_mil_sec
from core.utils.handle_card_event import handle_card_event
from shuttle.models import TsKv, TsKvDictionary, TsKvLatest
from shuttle.services.card_log_updates import publish_card_log_updates_batch
from shuttle.tasks import publish_updates_batch_task, update_activity_device_task
from shuttle.utils.find_compatible_field import find_compatible_field

redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

logger = logging.getLogger(__name__)

# Increased from 3600s (1h) to 7200s (2h) - TsKvDictionary rarely changes
EXPIRY_TIME = 7200

# Process-local in-memory cache for TsKvDictionary (2-tier: memory → Redis → DB)
# Dictionary keys are stable, so can cache aggressively
_TSKV_DICT_MEMORY_CACHE = {}
_TSKV_DICT_CACHE_TTL = 3600  # 1 hour


class TsKvDictionaryType(DefaultDict):
    key_id: str
    key: str


def get_tskv_dict(key):
    """Get TsKvDictionary with 2-tier caching: memory → Redis → database"""
    logger.debug("Getting ts_kv_dictionary: %s", key)

    # Tier 1: Check in-memory cache
    current_time = get_mil_sec() // 1000
    cache_entry = _TSKV_DICT_MEMORY_CACHE.get(key)
    if cache_entry and (current_time - cache_entry["cached_at"]) < _TSKV_DICT_CACHE_TTL:
        logger.debug("TsKvDictionary found in memory cache: %s", key)
        return cache_entry["data"]

    # Tier 2: Check Redis cache
    cache_key = f"prs_msg:tskv_dict:{key}"
    cached_raw = redis_client.get(cache_key)
    cached_obj = cached_raw.decode("utf-8") if isinstance(cached_raw, bytes) else None

    if cached_obj:
        logger.debug("TsKvDictionary found in Redis cache: %s", cached_obj)
        data = json.loads(cached_obj)
        # Populate memory cache from Redis hit
        _TSKV_DICT_MEMORY_CACHE[key] = {"data": data, "cached_at": current_time}
        return data

    # Tier 3: Database lookup with get_or_create
    obj, _ = TsKvDictionary.objects.get_or_create(key=key)
    data = {
        "key_id": obj.key_id,
        "key": obj.key,
    }

    # Cache in both Redis and memory
    redis_client.set(cache_key, json.dumps(data), ex=EXPIRY_TIME)
    _TSKV_DICT_MEMORY_CACHE[key] = {"data": data, "cached_at": current_time}

    return data


executor = ThreadPoolExecutor(max_workers=4)  # для handle_fias


def sync_telemetry(device, topic, payload):
    if topic.startswith("v1/gateway/") and isinstance(payload, dict):
        for sub_name, telemetry_list in payload.items():
            device = get_sub_device(device, name=sub_name)
            payload = telemetry_list

    device_id = device.get("id")
    entries = []
    logger.debug(
        "Sync telemetry: device=%s topic=%s entries=%s",
        device_id,
        topic,
        len(payload) if hasattr(payload, "__len__") else 1,
    )

    if isinstance(payload, dict) and "ts" in payload and "values" in payload:
        entries.append((payload["ts"], payload["values"]))
    elif isinstance(payload, list):
        entries.extend((d["ts"], d["values"]) for d in payload if isinstance(d, dict) and "ts" in d and "values" in d)
    if not entries:
        logger.warning("No valid telemetry entries found for device %s", device_id)
        return

    ts_now = get_mil_sec()
    historical_objs = []
    latest_objs = []
    card_logs = []
    updates_by_device: dict[str, list[dict]] = DefaultDict(list)

    for ts_ms, vals in entries:
        ts_dt = unix_to_datetime(ts_ms)
        for key, (field, value) in find_compatible_field(vals).items():
            if key == "rfid_card_event":
                card_log = handle_card_event(device, value, ts_dt)
                if card_log:
                    card_logs.append(card_log)
                continue
            dict_obj = get_tskv_dict(key)
            historical_objs.append(TsKv(entity_id=device_id, key_id=dict_obj.get("key_id"), ts=ts_dt, **{field: value}))
            latest_objs.append(
                TsKvLatest(entity_id=device_id, key_id=dict_obj.get("key_id"), ts=ts_now, **{field: value})
            )
            # пакетное сообщение в Redis
            updates_by_device[f"{device_id}_{device.get('tenant_id')}"].append(
                {
                    "entity": str(device_id),
                    "key": key,
                    "ts": ts_now,
                    "bool_v": value if field == "bool_v" else None,
                    "str_v": value if field == "str_v" else None,
                    "long_v": value if field == "long_v" else None,
                    "dbl_v": value if field == "dbl_v" else None,
                    "json_v": value if field == "json_v" else None,
                    "value": value,
                }
            )
            if key == "messageFromFIAS":
                executor.submit(handle_fias, value, device)

    TsKv.objects.bulk_create(historical_objs, batch_size=1000, ignore_conflicts=True)

    if latest_objs:
        try:
            unique = {(obj.entity_id, obj.key_id): obj for obj in latest_objs}
            TsKvLatest.objects.bulk_create(
                list(unique.values()),
                update_conflicts=True,
                update_fields=["ts", "bool_v", "str_v", "long_v", "dbl_v", "json_v"],
                unique_fields=["entity_id", "key_id"],
                batch_size=1000,
            )
        except Exception as e:
            logger.exception("Failed to upsert TsKvLatest: %s", e)

    if card_logs:
        try:
            CardLog.objects.bulk_create(
                card_logs,
                update_conflicts=True,
                batch_size=500,
                update_fields=["access_group", "staff", "guest", "additional_info"],
                unique_fields=["created_at", "number", "device_id"],
            )
            publish_card_log_updates_batch(card_logs)
        except Exception as e:
            logger.exception("Failed to create CardLog entries: %s", e)

    update_activity_device_task.delay(device_id)

    # Пакетная отправка всем подписанным WebSocket-клиентам
    if updates_by_device:
        publish_updates_batch_task.delay(updates_by_device)


def sync_telemetry_batch(batch: list[tuple]):
    """
    Process multiple telemetry messages in a single batch.
    batch: list of (device, topic, payload) tuples
    """
    ts_now = get_mil_sec()
    historical_objs = []
    latest_objs = []
    card_logs = []
    updates_by_device: dict[str, list[dict]] = DefaultDict(list)
    device_ids = set()

    for device, topic, payload in batch:
        if topic.startswith("v1/gateway/") and isinstance(payload, dict):
            for sub_name, telemetry_list in payload.items():
                sub_device = get_sub_device(device, name=sub_name)
                _process_telemetry_entries(
                    sub_device, telemetry_list, ts_now, historical_objs, latest_objs, card_logs, updates_by_device
                )
                device_ids.add(sub_device.get("id"))
        else:
            _process_telemetry_entries(
                device, payload, ts_now, historical_objs, latest_objs, card_logs, updates_by_device
            )
            device_ids.add(device.get("id"))

    # Bulk database operations
    if historical_objs:
        TsKv.objects.bulk_create(historical_objs, batch_size=1000, ignore_conflicts=True)

    if latest_objs:
        try:
            unique = {(obj.entity_id, obj.key_id): obj for obj in latest_objs}
            TsKvLatest.objects.bulk_create(
                list(unique.values()),
                update_conflicts=True,
                update_fields=["ts", "bool_v", "str_v", "long_v", "dbl_v", "json_v"],
                unique_fields=["entity_id", "key_id"],
                batch_size=1000,
            )
        except Exception as e:
            logger.exception("Failed to upsert TsKvLatest in batch: %s", e)

    if card_logs:
        try:
            CardLog.objects.bulk_create(
                card_logs,
                update_conflicts=True,
                batch_size=500,
                update_fields=["access_group", "staff", "guest", "additional_info"],
                unique_fields=["created_at", "number", "device_id"],
            )
            publish_card_log_updates_batch(card_logs)
        except Exception as e:
            logger.exception("Failed to create CardLog entries in batch: %s", e)

    # Update activity for all devices
    for device_id in device_ids:
        update_activity_device_task.delay(device_id)

    # Batch publish WebSocket updates
    if updates_by_device:
        publish_updates_batch_task.delay(updates_by_device)

    logger.debug(
        "Batch telemetry processed: %d messages, %d historical, %d latest",
        len(batch),
        len(historical_objs),
        len(latest_objs),
    )


def _process_telemetry_entries(device, payload, ts_now, historical_objs, latest_objs, card_logs, updates_by_device):
    """Helper function to process telemetry entries for a single device"""
    device_id = device.get("id")
    entries = []

    if isinstance(payload, dict) and "ts" in payload and "values" in payload:
        entries.append((payload["ts"], payload["values"]))
    elif isinstance(payload, list):
        entries.extend((d["ts"], d["values"]) for d in payload if isinstance(d, dict) and "ts" in d and "values" in d)

    if not entries:
        return

    for ts_ms, vals in entries:
        ts_dt = unix_to_datetime(ts_ms)
        for key, (field, value) in find_compatible_field(vals).items():
            if key == "rfid_card_event":
                card_log = handle_card_event(device, value, ts_dt)
                if card_log:
                    card_logs.append(card_log)
                continue

            dict_obj = get_tskv_dict(key)
            historical_objs.append(TsKv(entity_id=device_id, key_id=dict_obj.get("key_id"), ts=ts_dt, **{field: value}))
            latest_objs.append(
                TsKvLatest(entity_id=device_id, key_id=dict_obj.get("key_id"), ts=ts_now, **{field: value})
            )

            updates_by_device[f"{device_id}_{device.get('tenant_id')}"].append(
                {
                    "entity": str(device_id),
                    "key": key,
                    "ts": ts_now,
                    "bool_v": value if field == "bool_v" else None,
                    "str_v": value if field == "str_v" else None,
                    "long_v": value if field == "long_v" else None,
                    "dbl_v": value if field == "dbl_v" else None,
                    "json_v": value if field == "json_v" else None,
                    "value": value,
                }
            )

            if key == "messageFromFIAS":
                executor.submit(handle_fias, value, device)

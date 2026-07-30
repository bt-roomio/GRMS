import logging
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import orjson
from psycopg2 import errorcodes as pg_errorcodes

from access_manager.models import CardLog
from core.management.mq.devices.get_device import get_sub_device
from core.management.mq.fias import handle_fias
from core.utils.date import unix_to_datetime
from core.utils.get_time import get_mil_sec
from core.utils.handle_card_event import handle_card_event
from core.utils.redis_pool import sync_redis as redis_client
from shuttle.models import TsKv, TsKvDictionary, TsKvLatest
from shuttle.services.card_log_updates import publish_card_log_updates_batch
from shuttle.tasks import publish_updates_batch_task, update_activity_devices_batch_task
from shuttle.utils.find_compatible_field import find_compatible_field

logger = logging.getLogger(__name__)

_MAX_DEADLOCK_RETRIES = 3


def _upsert_latest(objects):
    """Upsert TsKvLatest with sort-before-insert and deadlock retry (pgcode 40P01)."""
    sorted_objs = sorted(objects, key=lambda o: (str(o.entity_id), str(o.key_id)))
    for attempt in range(_MAX_DEADLOCK_RETRIES):
        try:
            TsKvLatest.objects.bulk_create(
                sorted_objs,
                update_conflicts=True,
                update_fields=["ts", "bool_v", "str_v", "long_v", "dbl_v", "json_v"],
                unique_fields=["entity_id", "key_id"],
                batch_size=1000,
            )
            return
        except Exception as exc:
            pgcode = getattr(getattr(exc, "__cause__", None), "pgcode", None)
            if pgcode == pg_errorcodes.DEADLOCK_DETECTED and attempt < _MAX_DEADLOCK_RETRIES - 1:
                time.sleep(0.05 * (2**attempt))
                continue
            raise


def _upsert_card_logs(card_logs):
    """Upsert CardLog with sort-before-insert and deadlock retry (pgcode 40P01)."""
    sorted_logs = sorted(card_logs, key=lambda o: (str(o.created_at), str(o.number), str(o.device_id)))
    for attempt in range(_MAX_DEADLOCK_RETRIES):
        try:
            CardLog.objects.bulk_create(
                sorted_logs,
                update_conflicts=True,
                batch_size=500,
                update_fields=["access_group", "staff", "guest", "additional_info"],
                unique_fields=["created_at", "number", "device_id"],
            )
            return
        except Exception as exc:
            pgcode = getattr(getattr(exc, "__cause__", None), "pgcode", None)
            if pgcode == pg_errorcodes.DEADLOCK_DETECTED and attempt < _MAX_DEADLOCK_RETRIES - 1:
                time.sleep(0.05 * (2**attempt))
                continue
            raise


# Increased from 3600s (1h) to 7200s (2h) - TsKvDictionary rarely changes
EXPIRY_TIME = 7200

# Process-local in-memory cache for TsKvDictionary (2-tier: memory → Redis → DB)
# Dictionary keys are stable, so can cache aggressively
_TSKV_DICT_MEMORY_CACHE = {}
_TSKV_DICT_CACHE_TTL = 3600  # 1 hour


class TsKvDictionaryType(defaultdict):
    key_id: str
    key: str


def get_tskv_dict(key):
    """Get TsKvDictionary with 2-tier caching: memory → Redis → database"""
    logger.debug("Getting ts_kv_dictionary: %s", key)

    # Tier 1: Check in-memory cache
    current_time = get_mil_sec() // 1000
    cache_entry = _TSKV_DICT_MEMORY_CACHE.get(key)
    if cache_entry and (current_time - cache_entry["cached_at"]) < _TSKV_DICT_CACHE_TTL:
        return cache_entry["data"]

    # Tier 2: Check Redis cache
    cache_key = f"prs_msg:tskv_dict:{key}"
    cached_raw = redis_client.get(cache_key)
    cached_obj = cached_raw.decode("utf-8") if isinstance(cached_raw, bytes) else None

    if cached_obj:
        data = orjson.loads(cached_obj)
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
    redis_client.set(cache_key, orjson.dumps(data), ex=EXPIRY_TIME)
    _TSKV_DICT_MEMORY_CACHE[key] = {"data": data, "cached_at": current_time}

    return data


def get_tskv_dicts_batch(keys) -> dict:
    """Resolve many TsKvDictionary keys at once: memory → one Redis MGET → DB for misses.

    Populates the process-local + Redis caches so subsequent per-key ``get_tskv_dict()``
    calls in the batch hit memory instead of doing a Redis/DB round-trip per key.
    """
    keys = [key for key in dict.fromkeys(keys) if key]
    result: dict = {}
    if not keys:
        return result

    current_time = get_mil_sec() // 1000

    redis_misses = []
    for key in keys:
        entry = _TSKV_DICT_MEMORY_CACHE.get(key)
        if entry and (current_time - entry["cached_at"]) < _TSKV_DICT_CACHE_TTL:
            result[key] = entry["data"]
        else:
            redis_misses.append(key)

    if not redis_misses:
        return result

    raws = redis_client.mget([f"prs_msg:tskv_dict:{key}" for key in redis_misses])
    db_misses = []
    for key, raw in zip(redis_misses, raws):  # ty: ignore
        if raw:
            data = orjson.loads(raw)
            _TSKV_DICT_MEMORY_CACHE[key] = {"data": data, "cached_at": current_time}
            result[key] = data
        else:
            db_misses.append(key)

    if db_misses:
        pipe = redis_client.pipeline()
        for key in db_misses:
            obj, _ = TsKvDictionary.objects.get_or_create(key=key)
            data = {"key_id": obj.key_id, "key": obj.key}
            result[key] = data
            _TSKV_DICT_MEMORY_CACHE[key] = {"data": data, "cached_at": current_time}
            pipe.set(f"prs_msg:tskv_dict:{key}", orjson.dumps(data), ex=EXPIRY_TIME)
        pipe.execute()

    return result


def _collect_value_keys(payload, keys: set):
    """Collect telemetry value keys from a single device payload (dict or list of entries)."""
    entries = []
    if isinstance(payload, dict) and "ts" in payload and "values" in payload:
        entries = [payload["values"]]
    elif isinstance(payload, list):
        entries = [e["values"] for e in payload if isinstance(e, dict) and "ts" in e and "values" in e]
    for values in entries:
        if isinstance(values, dict):
            # Только ключи, которые реально запишутся: _process_telemetry_entries тоже
            # фильтрует через find_compatible_field, поэтому не прогреваем/не создаём
            # TsKvDictionary для нехранимых значений (например None).
            keys.update(find_compatible_field(values).keys())


def _warm_tskv_dict_cache(batch):
    """Pre-resolve every TsKvDictionary key in the batch in one pass.

    Afterwards the per-key get_tskv_dict() calls in _process_telemetry_entries hit
    the memory cache. rfid_card_event is excluded — it maps to CardLog, not a dict row.
    """
    keys: set = set()
    for _device, topic, payload in batch:
        if topic.startswith("v1/gateway/") and isinstance(payload, dict):
            for telemetry_list in payload.values():
                _collect_value_keys(telemetry_list, keys)
        else:
            _collect_value_keys(payload, keys)
    keys.discard("rfid_card_event")
    if keys:
        get_tskv_dicts_batch(keys)


executor = ThreadPoolExecutor(max_workers=4)  # для handle_fias


def _log_fias_result(future):
    """Surface exceptions from fire-and-forget handle_fias() submissions."""
    exc = future.exception()
    if exc is not None:
        logger.error("handle_fias failed: %s", exc, exc_info=exc)


def sync_telemetry_batch(batch: list[tuple]):
    """
    Process multiple telemetry messages in a single batch.
    batch: list of (device, topic, payload) tuples
    """
    ts_now = get_mil_sec()
    historical_objs = []
    latest_objs = []
    card_logs = []
    updates_by_device: dict[str, list[dict]] = defaultdict(list)
    device_ids = set()

    # Pre-resolve all TsKvDictionary keys in one pass so per-key lookups below hit memory
    _warm_tskv_dict_cache(batch)

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
            _upsert_latest(list(unique.values()))
        except Exception as e:
            logger.exception("Failed to upsert TsKvLatest in batch: %s", e)

    if card_logs:
        try:
            _upsert_card_logs(card_logs)
            publish_card_log_updates_batch(card_logs)
        except Exception as e:
            logger.exception("Failed to create CardLog entries in batch: %s", e)

    # One Celery task for all devices instead of N separate dispatches
    if device_ids:
        update_activity_devices_batch_task.delay(list(device_ids))

    # Batch publish WebSocket updates
    if updates_by_device:
        logger.info("Dispatching publish_updates_batch_task: devices=%s", len(updates_by_device.keys()))
        publish_updates_batch_task.delay(updates_by_device)

    logger.info(
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
                executor.submit(handle_fias, value, device).add_done_callback(_log_fias_result)

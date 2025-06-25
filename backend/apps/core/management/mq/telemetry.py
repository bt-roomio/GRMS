import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import DefaultDict

import redis
from access_manager.models import CardLog
from django.conf import settings

from core.management.handle_fias import handle_fias
from core.management.mq.get_device import get_sub_device
from core.management.mq.state_device import update_activity_device
from core.utils.date import unix_to_datetime
from core.utils.get_time import get_mil_sec
from core.utils.handle_card_event import handle_card_event
from shuttle.models import TsKv, TsKvDictionary, TsKvLatest
from shuttle.services.card_log_updates import publish_card_log_updates_batch
from shuttle.services.ts_kv_latest import publish_updates_batch
from shuttle.utils.find_compatible_field import find_compatible_field

redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

EXPIRY_TIME = 3600


class TsKvDictionaryType(DefaultDict):
    key_id: str
    key: str


def get_tskv_dict(key):
    logger.debug("Getting ts_kv_dictionary: %s", key)
    cache_key = f"prs_msg:tskv_dict:{key}"
    cached_raw = redis_client.get(cache_key)
    cached_obj = cached_raw.decode("utf-8") if isinstance(cached_raw, bytes) else None

    if cached_obj:
        logger.debug("TsKvDictionary found in cache: %s", cached_obj)
        return json.loads(cached_obj)

    obj, _ = TsKvDictionary.objects.get_or_create(key=key)
    data = {
        "key_id": obj.key_id,
        "key": obj.key,
    }
    redis_client.set(cache_key, json.dumps(data), ex=EXPIRY_TIME)

    return data


executor = ThreadPoolExecutor(max_workers=4)  # для handle_fias


def sync_telemetry(device, topic, payload):
    logger.debug(
        "Sync telemetry: device=%s topic=%s entries=%s",
        device.get("id"),
        topic,
        len(payload) if hasattr(payload, "__len__") else 1,
    )

    if topic.startswith("v1/gateway/") and isinstance(payload, dict):
        for sub_name, telemetry_list in payload.items():
            device = get_sub_device(device, name=sub_name)
            payload = telemetry_list

    device_id = device.get("id")
    # # Собираем raw-entries [(ts_ms, values), …]
    entries = []
    if isinstance(payload, dict) and "ts" in payload and "values" in payload:
        entries.append((payload["ts"], payload["values"]))
    elif isinstance(payload, list):
        entries.extend((d["ts"], d["values"]) for d in payload if isinstance(d, dict) and "ts" in d and "values" in d)
    if not entries:
        return

    ts_now = get_mil_sec()
    historical_objs = []
    latest_objs = []
    card_logs = []
    updates_by_device: dict[str, list[dict]] = DefaultDict(list)

    # Формируем объекты и пакетные updates
    for ts_ms, vals in entries:
        ts_dt = unix_to_datetime(ts_ms)
        for key, (field, value) in find_compatible_field(vals).items():
            if key == "rfid_card_event":
                card_log = handle_card_event(device, value, ts_dt)
                if card_log:
                    card_logs.append(card_log)
                continue
            dict_obj = get_tskv_dict(key)
            # # исторические записи
            historical_objs.append(TsKv(entity_id=device_id, key_id=dict_obj.get("key_id"), ts=ts_dt, **{field: value}))
            # # объекты для upsert
            latest_objs.append(
                TsKvLatest(entity_id=device_id, key_id=dict_obj.get("key_id"), ts=ts_now, **{field: value})
            )
            # пакетное сообщение
            updates_by_device[str(device_id)].append(
                {
                    "entity": str(device_id),
                    "key": key,
                    "ts": ts_now,
                    "bool_v": value if field == "bool_v" else None,
                    "str_v": value if field == "str_v" else None,
                    "long_v": value if field == "long_v" else None,
                    "dbl_v": value if field == "dbl_v" else None,
                    "json_v": value if field == "json_v" else None,
                }
            )

            if key == "messageFromFIAS":
                # Асинхронный обработчик
                executor.submit(handle_fias, value, device)

    # # Сохраняем исторические данные
    TsKv.objects.bulk_create(historical_objs, batch_size=1000, ignore_conflicts=True)

    if card_logs:
        try:
            CardLog.objects.bulk_create(card_logs, ignore_conflicts=True)
            publish_card_log_updates_batch(card_logs)
        except Exception as e:
            logger.exception("Failed to create CardLog entries: %s", e)

    # Upsert последних значений
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

    # Пакетная отправка всем подписанным WebSocket-клиентам
    if updates_by_device:
        publish_updates_batch(updates_by_device)

    # Обновляем активность устройства
    # 0.03 sec goes
    update_activity_device(device.get("id"))

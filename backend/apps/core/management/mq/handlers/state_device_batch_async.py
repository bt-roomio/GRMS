"""Async версия state_device_batch для использования в mq_async.py"""

import logging
from collections import defaultdict

from asgiref.sync import sync_to_async
from django.db import close_old_connections

from core.management.mq.devices.get_device import get_sub_device
from core.utils.cache import invalidate_quick_cache
from core.utils.get_time import get_mil_sec
from main.models import Device
from main.observables.device import publish_device
from main.observables.room_status_async import publish_room_status_async
from shuttle.models import AttributeKv
from shuttle.services.attribute_kv_async import publish_updates_attribute_batch_async
from shuttle.utils.has_changed_and_update import (
    get_cached_attributes_batch,
    invalidate_attributes_cache,
    set_cached_attributes,
)

logger = logging.getLogger("core")


async def sync_state_device_batch_async(batch: list[tuple]):
    """
    Async версия sync_state_device_batch для использования в асинхронном контексте.
    Process multiple device connect/disconnect messages in a single batch.

    Args:
        batch: list of (device, topic, data) tuples
    """
    if not batch:
        return

    logger.debug("[state_device_batch_async] Processing batch: %d messages", len(batch))

    ts_now = get_mil_sec()

    # Группировка обновлений по device_id
    device_updates = defaultdict(
        lambda: {
            "connected": None,
            "device_obj": None,
            "tenant_id": None,
            "device_status": None,
            "from_cache": False,
            "cached_tenant_id": None,
            "cached_device_status": None,
        }
    )

    # Шаг 1: Парсинг и группировка сообщений
    for device, topic, data in batch:
        sub_device_name = data.get("device")
        device_type = data.get("type")

        def _get_sub(_device=device, _name=sub_device_name, _dtype=device_type):
            close_old_connections()
            return get_sub_device(_device, name=_name, device_type=_dtype)

        sub = await sync_to_async(_get_sub, thread_sensitive=False)()
        sub_device_id = sub.get("id")
        connected = not topic.endswith("disconnect")

        device_updates[sub_device_id].update(
            {
                "connected": connected,
                "device_obj": sub,
                "parent_device": device,
            }
        )

    # Шаг 2: Загрузка существующих атрибутов — один MGET на весь батч, затем один SELECT на промахи
    attr_map_by_device = {}
    cached_by_device = get_cached_attributes_batch(
        [str(device_id) for device_id in device_updates], ["active", "lastActivityTime"], AttributeKv.SERVER_SCOPE
    )

    ids_needing_db = []
    for device_id, update_info in device_updates.items():
        cached_attrs = cached_by_device.get(str(device_id))

        if cached_attrs:
            attr_map = {}

            # Кешируем attr только если известен его pk (id): без pk bulk_update()
            # в Шаге 4 упал бы с ValueError. Если id в кеше нет — читаем из БД.
            if "active" in cached_attrs and "id" in cached_attrs["active"]:
                active_data = cached_attrs["active"]
                attr_map["active"] = AttributeKv(
                    id=active_data["id"],
                    entity_id=device_id,
                    attribute_key="active",
                    attribute_type=AttributeKv.SERVER_SCOPE,
                    bool_v=active_data["bool_v"],
                    last_update_ts=active_data["last_update_ts"],
                )
                update_info["cached_tenant_id"] = active_data["tenant_id"]
                update_info["cached_device_status"] = active_data.get("status", False)

            if "lastActivityTime" in cached_attrs and "id" in cached_attrs["lastActivityTime"]:
                last_data = cached_attrs["lastActivityTime"]
                attr_map["lastActivityTime"] = AttributeKv(
                    id=last_data["id"],
                    entity_id=device_id,
                    attribute_key="lastActivityTime",
                    attribute_type=AttributeKv.SERVER_SCOPE,
                    long_v=last_data["long_v"],
                    last_update_ts=last_data["last_update_ts"],
                )
                if not update_info["cached_tenant_id"]:
                    update_info["cached_tenant_id"] = last_data["tenant_id"]

            if attr_map:
                update_info["from_cache"] = True
                attr_map_by_device[device_id] = attr_map
            else:
                ids_needing_db.append(device_id)
        else:
            ids_needing_db.append(device_id)

    if ids_needing_db:

        def _query_attrs(_ids=ids_needing_db):
            close_old_connections()
            return list(
                AttributeKv.objects.filter(
                    entity_id__in=_ids,
                    attribute_type=AttributeKv.SERVER_SCOPE,
                    attribute_key__in=["active", "lastActivityTime"],
                ).order_by()
            )

        attrs = await sync_to_async(_query_attrs, thread_sensitive=False)()
        by_device = defaultdict(dict)
        for attr in attrs:
            by_device[str(attr.entity_id)][attr.attribute_key] = attr
        for device_id in ids_needing_db:
            attr_map_by_device[device_id] = by_device.get(str(device_id), {})

    # === Шаг 2.5: Batched device info (tenant_id, status) ===
    device_ids = list(device_updates.keys())

    def _query_device_info(_ids=device_ids):
        close_old_connections()
        return list(Device.objects.filter(id__in=_ids).values("id", "tenant_id", "status"))

    device_info_rows = await sync_to_async(_query_device_info, thread_sensitive=False)()
    device_info_by_id = {str(r["id"]): r for r in device_info_rows}

    # Шаг 3: Подготовка bulk операций
    to_update = []
    to_create = []
    devices_to_update_status = []
    devices_to_invalidate_cache = set()
    devices_with_creates = set()  # устройства с bulk_create — их id клиентские (None), не кешируем

    for device_id, update_info in device_updates.items():
        connected = update_info["connected"]
        from_cache = update_info["from_cache"]
        attr_map = attr_map_by_device.get(device_id, {})

        active_attr = attr_map.get("active")
        last_activity_attr = attr_map.get("lastActivityTime")

        # Debounce check (3 sec threshold)
        if connected and active_attr and active_attr.bool_v == connected and active_attr.last_update_ts > ts_now - 3000:
            continue

        device_needs_update = False

        # Process active attribute
        if active_attr:
            if active_attr.bool_v != connected:
                active_attr.bool_v = connected
                active_attr.last_update_ts = ts_now
                active_attr.entity_type = "DEVICE"
                to_update.append(active_attr)

            info = device_info_by_id.get(str(device_id))
            current_device_status = (
                update_info["cached_device_status"] if from_cache else (info["status"] if info else False)
            )
            if current_device_status != connected:
                device_needs_update = True
        else:
            to_create.append(
                AttributeKv(
                    entity_id=device_id,
                    attribute_key="active",
                    entity_type="DEVICE",
                    attribute_type=AttributeKv.SERVER_SCOPE,
                    bool_v=connected,
                    last_update_ts=ts_now,
                )
            )
            devices_with_creates.add(device_id)

        # Process lastActivityTime attribute
        if last_activity_attr:
            if last_activity_attr.long_v != ts_now:
                last_activity_attr.long_v = ts_now
                last_activity_attr.last_update_ts = ts_now
                last_activity_attr.entity_type = "DEVICE"
                to_update.append(last_activity_attr)
        else:
            to_create.append(
                AttributeKv(
                    entity_id=device_id,
                    attribute_key="lastActivityTime",
                    entity_type="DEVICE",
                    attribute_type=AttributeKv.SERVER_SCOPE,
                    long_v=ts_now,
                    last_update_ts=ts_now,
                )
            )
            devices_with_creates.add(device_id)

        if device_needs_update:
            devices_to_update_status.append((device_id, connected))
            devices_to_invalidate_cache.add(str(device_id))

        update_info["device_needs_update"] = device_needs_update

        # ВАЖНО: Сравниваем строковые представления, так как типы могут отличаться (UUID vs str)
        device_id_str = str(device_id)
        update_info["to_update_attrs"] = [a for a in to_update if str(a.entity_id) == device_id_str]  # ty: ignore
        update_info["to_create_attrs"] = [a for a in to_create if str(a.entity_id) == device_id_str]  # ty: ignore

    logger.debug(
        "[state_device_batch_async] Prepared: %d updates, %d creates, %d device status updates",
        len(to_update),
        len(to_create),
        len(devices_to_update_status),
    )

    # Шаг 4: Bulk DB operations (async)
    if to_update:

        def _bulk_update(_attrs=to_update):
            close_old_connections()
            AttributeKv.objects.bulk_update(_attrs, fields=["bool_v", "long_v", "last_update_ts", "entity_type"])

        await sync_to_async(_bulk_update, thread_sensitive=False)()
        logger.debug("[state_device_batch_async] Bulk updated %d AttributeKv records", len(to_update))

    if to_create:

        def _bulk_create(_attrs=to_create):
            close_old_connections()
            AttributeKv.objects.bulk_create(_attrs, ignore_conflicts=True)

        await sync_to_async(_bulk_create, thread_sensitive=False)()
        logger.debug("[state_device_batch_async] Bulk created %d AttributeKv records", len(to_create))

        # Добавить созданные атрибуты в attr_map_by_device для WebSocket публикации
        for attr in to_create:
            if attr.entity_id not in attr_map_by_device:
                attr_map_by_device[attr.entity_id] = {}
            attr_map_by_device[attr.entity_id][attr.attribute_key] = attr

    if devices_to_update_status:
        connect_ids = [did for did, conn in devices_to_update_status if conn]
        disconnect_ids = [did for did, conn in devices_to_update_status if not conn]

        def _bulk_update_status(_cids=connect_ids, _dids=disconnect_ids):
            close_old_connections()
            if _cids:
                Device.objects.filter(id__in=_cids).update(status=True)
            if _dids:
                Device.objects.filter(id__in=_dids).update(status=False)

        await sync_to_async(_bulk_update_status, thread_sensitive=False)()
        logger.debug("[state_device_batch_async] Updated status for %d devices", len(devices_to_update_status))

    # Шаг 5: Cache invalidation
    for device_id_str in devices_to_invalidate_cache:
        invalidate_attributes_cache(device_id_str, AttributeKv.SERVER_SCOPE)

    if devices_to_invalidate_cache:
        logger.debug("[state_device_batch_async] Invalidated cache for %d devices", len(devices_to_invalidate_cache))

    # Шаг 6: WebSocket публикация и cache update
    if to_update or to_create:
        updates_by_device: dict[str, list[dict]] = defaultdict(list)
        cache_updates_by_device = {}

        for device_id, update_info in device_updates.items():
            from_cache = update_info["from_cache"]
            connected = update_info["connected"]
            device_needs_update = update_info.get("device_needs_update", False)
            attr_map = attr_map_by_device.get(device_id, {})

            if not update_info.get("to_update_attrs") and not update_info.get("to_create_attrs"):
                continue

            if from_cache:
                tenant_id = update_info["cached_tenant_id"]
            else:
                info = device_info_by_id.get(str(device_id))
                tenant_id = info["tenant_id"] if info else None

            device_key = f"{device_id}_{tenant_id}"

            info = device_info_by_id.get(str(device_id))
            db_status = info["status"] if info else False

            current_status = (
                connected if device_needs_update else (update_info["cached_device_status"] if from_cache else db_status)
            )

            cache_data = {}
            for attr_key, attr in attr_map.items():
                # WebSocket update
                updates_by_device[device_key].append(
                    {
                        "entity": str(device_id),
                        "key_name": attr_key,
                        "last_update_ts": ts_now,
                        "scope": AttributeKv.SERVER_SCOPE,
                        "value": attr.bool_v if attr_key == "active" else attr.long_v,
                    }
                )

                # Cache data (id обязателен — при чтении из кеша он нужен для bulk_update)
                cache_attr = {
                    "id": str(attr.id),
                    "entity_id": str(device_id),
                    "tenant_id": str(tenant_id),
                    "last_update_ts": attr.last_update_ts,
                }

                if attr_key == "active":
                    cache_attr["bool_v"] = attr.bool_v
                    cache_attr["status"] = current_status
                elif attr_key == "lastActivityTime":
                    cache_attr["long_v"] = attr.long_v

                cache_data[attr_key] = cache_attr

            # У устройств с bulk_create(ignore_conflicts) id атрибута сгенерирован на клиенте
            # (None) и может не совпасть с реально сохранённой строкой — не кешируем такой id,
            # следующий вызов сделает cache-miss и перечитает настоящий id из БД.
            if cache_data and device_id not in devices_with_creates:
                cache_updates_by_device[device_id] = cache_data

        # Async WebSocket publish
        if updates_by_device:
            await publish_updates_attribute_batch_async(updates_by_device)
            logger.debug(
                "[state_device_batch_async] Published WebSocket updates for %d devices", len(updates_by_device)
            )

        # Update Redis cache
        for device_id, cache_data in cache_updates_by_device.items():
            set_cached_attributes(str(device_id), cache_data, AttributeKv.SERVER_SCOPE, ttl=5)

        if cache_updates_by_device:
            logger.debug("[state_device_batch_async] Updated cache for %d devices", len(cache_updates_by_device))

    # Шаг 7: Room status publication (NO attr.entity, batched fetch)
    device_ids_for_room_status = [
        device_id for device_id, update_info in device_updates.items() if update_info.get("device_needs_update")
    ]

    devices_for_room_status = []
    if device_ids_for_room_status:

        def _query_devices_for_room(_ids=device_ids_for_room_status):
            close_old_connections()
            return list(Device.objects.filter(id__in=_ids))

        devices_for_room_status = await sync_to_async(_query_devices_for_room, thread_sensitive=False)()

    tenant_ids_to_invalidate = set()
    for device in devices_for_room_status:
        try:
            await publish_room_status_async(device)
            await sync_to_async(publish_device, thread_sensitive=True)(device)
            tenant_ids_to_invalidate.add(device.tenant_id)
        except Exception as e:
            logger.warning("Failed to publish room status for device %s: %s", device.id, e)

    for tenant_id in tenant_ids_to_invalidate:
        invalidate_quick_cache("devices", tenant_id)

    if devices_for_room_status:
        logger.debug("[state_device_batch_async] Published room status for %d devices", len(devices_for_room_status))

    logger.info(
        "[state_device_batch_async] Completed batch processing: %d messages, %d devices",
        len(batch),
        len(device_updates),
    )

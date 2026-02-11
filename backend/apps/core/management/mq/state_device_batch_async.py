"""Async версия state_device_batch для использования в mq_async.py"""

import logging
from collections import defaultdict

from asgiref.sync import sync_to_async

from core.management.mq.get_device import get_sub_device
from core.utils.get_time import get_mil_sec
from main.models import Device
from main.observables.room_status_async import publish_room_status_async
from shuttle.models import AttributeKv
from shuttle.services.attribute_kv_async import publish_updates_attribute_batch_async
from shuttle.utils.has_changed_and_update import (
    get_cached_attributes,
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

    logger.debug(f"[state_device_batch_async] Processing batch: {len(batch)} messages")

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
        device_id = device.get("id")
        sub_device_name = data.get("device")
        sub = await sync_to_async(get_sub_device, thread_sensitive=True)(device, name=sub_device_name)
        sub_device_id = sub.get("id")
        connected = not topic.endswith("disconnect")

        device_updates[sub_device_id].update(
            {
                "connected": connected,
                "device_obj": sub,
                "parent_device": device,
            }
        )

    logger.debug(f"[state_device_batch_async] Grouped into {len(device_updates)} unique devices")

    # Шаг 2: Загрузка существующих атрибутов (из кеша или БД)
    attr_map_by_device = {}

    for device_id, update_info in device_updates.items():
        cached_attrs = get_cached_attributes(str(device_id), ["active", "lastActivityTime"], AttributeKv.SERVER_SCOPE)

        if cached_attrs:
            logger.debug(f"Cache hit for device {device_id}")
            update_info["from_cache"] = True

            attr_map = {}

            if "active" in cached_attrs:
                active_data = cached_attrs["active"]
                active_attr = AttributeKv(
                    entity_id=device_id,
                    attribute_key="active",
                    attribute_type=AttributeKv.SERVER_SCOPE,
                    bool_v=active_data["bool_v"],
                    last_update_ts=active_data["last_update_ts"],
                )
                update_info["cached_tenant_id"] = active_data["tenant_id"]
                update_info["cached_device_status"] = active_data.get("status", False)
                attr_map["active"] = active_attr

            if "lastActivityTime" in cached_attrs:
                last_data = cached_attrs["lastActivityTime"]
                last_activity_attr = AttributeKv(
                    entity_id=device_id,
                    attribute_key="lastActivityTime",
                    attribute_type=AttributeKv.SERVER_SCOPE,
                    long_v=last_data["long_v"],
                    last_update_ts=last_data["last_update_ts"],
                )
                if not update_info["cached_tenant_id"]:
                    update_info["cached_tenant_id"] = last_data["tenant_id"]
                attr_map["lastActivityTime"] = last_activity_attr

            attr_map_by_device[device_id] = attr_map
        else:
            logger.debug(f"Cache miss for device {device_id}, querying DB")
            # Async DB query
            attrs = await sync_to_async(
                lambda: list(
                    AttributeKv.objects.filter(
                        entity_id=device_id,
                        attribute_type=AttributeKv.SERVER_SCOPE,
                        attribute_key__in=["active", "lastActivityTime"],
                    ).select_related("entity")
                ),
                thread_sensitive=True,
            )()

            attr_map = {attr.attribute_key: attr for attr in attrs}
            attr_map_by_device[device_id] = attr_map

    logger.debug(f"[state_device_batch_async] Loaded attributes for {len(attr_map_by_device)} devices")

    # Шаг 3: Подготовка bulk операций
    to_update = []
    to_create = []
    devices_to_update_status = []
    devices_to_invalidate_cache = set()

    for device_id, update_info in device_updates.items():
        connected = update_info["connected"]
        from_cache = update_info["from_cache"]
        attr_map = attr_map_by_device.get(device_id, {})

        active_attr = attr_map.get("active")
        last_activity_attr = attr_map.get("lastActivityTime")

        # Debounce check (3 sec threshold)
        if connected and active_attr and active_attr.bool_v == connected and active_attr.last_update_ts > ts_now - 3000:
            logger.debug(f"Debounce: skipping device {device_id}")
            continue

        device_needs_update = False

        # Process active attribute
        if active_attr:
            if active_attr.bool_v != connected:
                active_attr.bool_v = connected
                active_attr.last_update_ts = ts_now
                active_attr.entity_type = "DEVICE"
                to_update.append(active_attr)

            current_device_status = (
                update_info["cached_device_status"]
                if from_cache
                else (active_attr.entity.status if hasattr(active_attr, "entity") else False)
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

        if device_needs_update:
            devices_to_update_status.append((device_id, connected))
            devices_to_invalidate_cache.add(str(device_id))

        update_info["device_needs_update"] = device_needs_update

        # ВАЖНО: Сравниваем строковые представления, так как типы могут отличаться (UUID vs str)
        device_id_str = str(device_id)
        update_info["to_update_attrs"] = [a for a in to_update if str(a.entity_id) == device_id_str]
        update_info["to_create_attrs"] = [a for a in to_create if str(a.entity_id) == device_id_str]

        logger.debug(
            f"[state_device_batch_async] Set for device {device_id} (type={type(device_id).__name__}): "
            f"to_update_attrs={len(update_info['to_update_attrs'])}, to_create_attrs={len(update_info['to_create_attrs'])}"
        )
        if to_update:
            logger.debug(
                f"[state_device_batch_async] First to_update attr entity_id type: {type(to_update[0].entity_id).__name__}"
            )

    logger.debug(
        f"[state_device_batch_async] Prepared: {len(to_update)} updates, {len(to_create)} creates, "
        f"{len(devices_to_update_status)} device status updates"
    )
    if to_update:
        logger.debug(f"[state_device_batch_async] to_update entity_ids: {[str(a.entity_id) for a in to_update]}")
    logger.debug(f"[state_device_batch_async] device_updates keys: {list(device_updates.keys())}")

    # Шаг 4: Bulk DB operations (async)
    if to_update:
        await sync_to_async(
            lambda: AttributeKv.objects.bulk_update(
                to_update, fields=["bool_v", "long_v", "last_update_ts", "entity_type"]
            ),
            thread_sensitive=True,
        )()
        logger.debug(f"[state_device_batch_async] Bulk updated {len(to_update)} AttributeKv records")

    if to_create:
        await sync_to_async(
            lambda: AttributeKv.objects.bulk_create(to_create, ignore_conflicts=True),
            thread_sensitive=True,
        )()
        logger.debug(f"[state_device_batch_async] Bulk created {len(to_create)} AttributeKv records")

        # Добавить созданные атрибуты в attr_map_by_device для WebSocket публикации
        for attr in to_create:
            if attr.entity_id not in attr_map_by_device:
                attr_map_by_device[attr.entity_id] = {}
            attr_map_by_device[attr.entity_id][attr.attribute_key] = attr

    if devices_to_update_status:
        for device_id, connected in devices_to_update_status:
            await sync_to_async(
                lambda did=device_id, conn=connected: Device.objects.filter(id=did).update(status=conn),
                thread_sensitive=True,
            )()
        logger.debug(f"[state_device_batch_async] Updated status for {len(devices_to_update_status)} devices")

    # Шаг 5: Cache invalidation
    for device_id_str in devices_to_invalidate_cache:
        invalidate_attributes_cache(device_id_str, AttributeKv.SERVER_SCOPE)

    if devices_to_invalidate_cache:
        logger.debug(f"[state_device_batch_async] Invalidated cache for {len(devices_to_invalidate_cache)} devices")

    # Шаг 6: WebSocket публикация и cache update
    if to_update or to_create:
        updates_by_device: dict[str, list[dict]] = defaultdict(list)
        cache_updates_by_device = {}

        for device_id, update_info in device_updates.items():
            from_cache = update_info["from_cache"]
            connected = update_info["connected"]
            device_needs_update = update_info.get("device_needs_update", False)
            attr_map = attr_map_by_device.get(device_id, {})

            logger.debug(
                f"[state_device_batch_async] Device {device_id}: to_update_attrs={len(update_info.get('to_update_attrs', []))}, "
                f"to_create_attrs={len(update_info.get('to_create_attrs', []))}, attr_map={list(attr_map.keys())}"
            )

            if not update_info.get("to_update_attrs") and not update_info.get("to_create_attrs"):
                logger.debug(f"[state_device_batch_async] Skipping device {device_id} - no attribute changes")
                continue

            # Get tenant_id
            if from_cache:
                tenant_id = update_info["cached_tenant_id"]
            else:
                active_attr = attr_map.get("active")
                last_activity_attr = attr_map.get("lastActivityTime")
                if active_attr and hasattr(active_attr, "entity"):
                    tenant_id = active_attr.entity.tenant_id
                elif last_activity_attr and hasattr(last_activity_attr, "entity"):
                    tenant_id = last_activity_attr.entity.tenant_id
                else:
                    device = await Device.objects.aget(id=device_id)
                    tenant_id = device.tenant_id

            device_key = f"{device_id}_{tenant_id}"

            current_status = (
                connected
                if device_needs_update
                else (
                    update_info["cached_device_status"]
                    if from_cache
                    else (
                        attr_map["active"].entity.status
                        if "active" in attr_map and hasattr(attr_map["active"], "entity")
                        else False
                    )
                )
            )

            cache_data = {}
            for attr_key, attr in attr_map.items():
                logger.debug(f"[state_device_batch_async] Preparing update for device {device_id}, attr {attr_key}")
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

                # Cache data
                cache_attr = {
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

            if cache_data:
                cache_updates_by_device[device_id] = cache_data

        # Async WebSocket publish
        if updates_by_device:
            await publish_updates_attribute_batch_async(updates_by_device)
            logger.debug(f"[state_device_batch_async] Published WebSocket updates for {len(updates_by_device)} devices")

        # Update Redis cache
        for device_id, cache_data in cache_updates_by_device.items():
            set_cached_attributes(str(device_id), cache_data, AttributeKv.SERVER_SCOPE, ttl=5)

        if cache_updates_by_device:
            logger.debug(f"[state_device_batch_async] Updated cache for {len(cache_updates_by_device)} devices")

    # Шаг 7: Room status publication
    devices_for_room_status = []
    for device_id, update_info in device_updates.items():
        if update_info.get("device_needs_update"):
            from_cache = update_info["from_cache"]
            if from_cache:
                device = await Device.objects.aget(id=device_id)
                devices_for_room_status.append(device)
            else:
                attr_map = attr_map_by_device.get(device_id, {})
                active_attr = attr_map.get("active")
                if active_attr and hasattr(active_attr, "entity"):
                    devices_for_room_status.append(active_attr.entity)

    for device in devices_for_room_status:
        try:
            await publish_room_status_async(device)
        except Exception as e:
            logger.warning(f"Failed to publish room status for device {device.id}: {e}")

    if devices_for_room_status:
        logger.debug(f"[state_device_batch_async] Published room status for {len(devices_for_room_status)} devices")

    logger.info(
        f"[state_device_batch_async] Completed batch processing: {len(batch)} messages, {len(device_updates)} devices"
    )

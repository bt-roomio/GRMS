import logging
from collections import defaultdict

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from core.utils.get_time import get_mil_sec
from main.models import Device
from main.serializers.device import SimpleDeviceSerializer
from shuttle.models import AttributeKv
from shuttle.services.attribute_kv import publish_updates_attribute_batch
from shuttle.utils.has_changed_and_update import (
    get_cached_attributes_batch,
    invalidate_attributes_cache,
    set_cached_attributes,
)

logger = logging.getLogger(__name__)


def _publish_status_batch(devices):
    """Публикация room_status/device для набора устройств одним пересечением границы
    sync↔async, вместо async_to_sync на каждый publish (~9.4 мс на вызов из-за подъёма
    event loop). room_status схлопываем по арендатору — это одна tenant-группа с
    одинаковым payload, слать её по разу на устройство бессмысленно."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    sends: list[tuple[str, dict]] = []
    seen_tenants: set = set()
    for device in devices:
        tenant_id = str(device.tenant_id)
        if tenant_id not in seen_tenants:
            seen_tenants.add(tenant_id)
            sends.append(
                (f"room_status_{tenant_id}", {"type": "get_latest_activity", "update": {"tenant_id": tenant_id}})
            )
        sends.append(
            (f"device_{tenant_id}", {"type": "device_latest_activity", "update": SimpleDeviceSerializer(device).data})
        )

    if not sends:
        return

    async def _fanout():
        for group_name, payload in sends:
            await channel_layer.group_send(group_name, payload)

    async_to_sync(_fanout)()


def update_activity_devices_batch(device_ids: list, connected: bool = True):
    """
    Батч-обработка активности устройств: обрабатывает список device_ids одним проходом
    (set-based запросы к БД и один WebSocket-паблиш) вместо N последовательных
    Redis/DB round-trip'ов на устройство. Структура повторяет state_device_batch_async.py.
    """
    if not device_ids:
        return

    device_ids = list(dict.fromkeys(device_ids))
    ts_now = get_mil_sec()

    attr_map_by_device: dict = {}
    from_cache_by_device: dict = {}
    cached_tenant_by_device: dict = {}
    cached_status_by_device: dict = {}
    ids_needing_db = []

    # Шаг 1: Redis кеш — один MGET на весь батч (как в state_device_batch_async)
    cached_by_device = get_cached_attributes_batch(
        [str(device_id) for device_id in device_ids], ["active", "lastActivityTime"], AttributeKv.SERVER_SCOPE
    )
    for device_id in device_ids:
        cached_attrs = cached_by_device.get(str(device_id))

        if cached_attrs:
            attr_map = {}

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
                cached_tenant_by_device[device_id] = active_data["tenant_id"]
                cached_status_by_device[device_id] = active_data.get("status", False)

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
                cached_tenant_by_device.setdefault(device_id, last_data["tenant_id"])

            if attr_map:
                attr_map_by_device[device_id] = attr_map
                from_cache_by_device[device_id] = True
            else:
                ids_needing_db.append(device_id)
                from_cache_by_device[device_id] = False
        else:
            ids_needing_db.append(device_id)
            from_cache_by_device[device_id] = False

    # Шаг 2: Один SELECT на все устройства с промахом кеша
    if ids_needing_db:
        attrs = AttributeKv.objects.filter(
            entity_id__in=ids_needing_db,
            attribute_type=AttributeKv.SERVER_SCOPE,
            attribute_key__in=["active", "lastActivityTime"],
        ).order_by()
        by_device: dict = defaultdict(dict)
        for attr in attrs:
            by_device[str(attr.entity_id)][attr.attribute_key] = attr
        for device_id in ids_needing_db:
            attr_map_by_device[device_id] = by_device.get(str(device_id), {})

    # Шаг 2.5: Один запрос Device (tenant_id, status) для устройств без кешированного tenant_id
    device_info_by_id: dict = {}
    ids_for_device_info = [d for d in device_ids if d not in cached_tenant_by_device]
    if ids_for_device_info:
        rows = Device.objects.filter(id__in=ids_for_device_info).values("id", "tenant_id", "status")
        device_info_by_id = {str(r["id"]): r for r in rows}

    # Шаг 3: Подготовка bulk-операций
    to_update = []
    to_create = []
    connect_ids = []
    disconnect_ids = []
    devices_to_invalidate_cache = set()
    device_needs_update_map: dict = {}
    skip_devices = set()
    devices_with_changes = set()  # устройства, у которых реально есть to_update/to_create
    devices_with_creates = set()  # устройства с bulk_create — их id клиентские, не кешируем

    for device_id in device_ids:
        from_cache = from_cache_by_device[device_id]
        attr_map = attr_map_by_device.get(device_id, {})
        active_attr = attr_map.get("active")
        last_activity_attr = attr_map.get("lastActivityTime")

        if (
            connected and active_attr and active_attr.bool_v == connected and active_attr.last_update_ts > ts_now - 3000
        ):  # 3 sec threshold (debounce mechanism)
            skip_devices.add(device_id)
            continue

        device_needs_update = False

        if active_attr:
            if active_attr.bool_v != connected:
                active_attr.bool_v = connected
                active_attr.last_update_ts = ts_now
                active_attr.entity_type = "DEVICE"
                to_update.append(active_attr)
                devices_with_changes.add(device_id)

            current_device_status = (
                cached_status_by_device.get(device_id)
                if from_cache
                else device_info_by_id.get(str(device_id), {}).get("status", False)
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
            devices_with_changes.add(device_id)
            devices_with_creates.add(device_id)

        if last_activity_attr:
            if last_activity_attr.long_v != ts_now:
                last_activity_attr.long_v = ts_now
                last_activity_attr.last_update_ts = ts_now
                last_activity_attr.entity_type = "DEVICE"
                to_update.append(last_activity_attr)
                devices_with_changes.add(device_id)
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
            devices_with_changes.add(device_id)
            devices_with_creates.add(device_id)

        if device_needs_update:
            (connect_ids if connected else disconnect_ids).append(device_id)
            devices_to_invalidate_cache.add(str(device_id))

        device_needs_update_map[device_id] = device_needs_update

    # Шаг 4: Bulk-запись в БД
    if to_update:
        AttributeKv.objects.bulk_update(to_update, fields=["bool_v", "long_v", "last_update_ts", "entity_type"])

    if to_create:
        AttributeKv.objects.bulk_create(to_create, ignore_conflicts=True)
        for attr in to_create:
            attr_map_by_device.setdefault(attr.entity_id, {})[attr.attribute_key] = attr

    if connect_ids:
        Device.objects.filter(id__in=connect_ids).update(status=True)
    if disconnect_ids:
        Device.objects.filter(id__in=disconnect_ids).update(status=False)

    for device_id_str in devices_to_invalidate_cache:
        invalidate_attributes_cache(device_id_str, AttributeKv.SERVER_SCOPE)

    # Шаг 5: Один WebSocket-паблиш и обновление кеша на весь батч
    if to_update or to_create:
        updates_by_device: dict = defaultdict(list)

        for device_id in device_ids:
            if device_id in skip_devices:
                continue

            # Публикуем/кешируем только устройства с реальными изменениями (как в оригинале)
            if device_id not in devices_with_changes:
                continue

            attr_map = attr_map_by_device.get(device_id, {})
            if not attr_map:
                continue

            from_cache = from_cache_by_device[device_id]
            device_needs_update = device_needs_update_map.get(device_id, False)

            tenant_id = cached_tenant_by_device.get(device_id) or device_info_by_id.get(str(device_id), {}).get(
                "tenant_id"
            )
            db_status = device_info_by_id.get(str(device_id), {}).get("status", False)
            current_status = (
                connected
                if device_needs_update
                else (cached_status_by_device.get(device_id) if from_cache else db_status)
            )

            device_key = f"{device_id}_{tenant_id}"
            cache_data = {}

            for attr_key, attr in attr_map.items():
                updates_by_device[device_key].append(
                    {
                        "entity": str(device_id),
                        "key_name": attr_key,
                        "last_update_ts": ts_now,
                        "scope": AttributeKv.SERVER_SCOPE,
                        "value": attr.bool_v if attr_key == "active" else attr.long_v,
                    }
                )

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
            # и при гонке создания может не совпасть с реально сохранённой строкой. Не кешируем
            # такой id — следующий вызов сделает cache-miss и перечитает настоящий id из БД.
            if cache_data and device_id not in devices_with_creates:
                set_cached_attributes(str(device_id), cache_data, AttributeKv.SERVER_SCOPE, ttl=5)

        if updates_by_device:
            publish_updates_attribute_batch(updates_by_device)

    # Шаг 6: Публикация room_status/device для устройств, у которых сменился статус
    ids_for_room_status = [d for d in device_ids if device_needs_update_map.get(d)]
    if ids_for_room_status:
        _publish_status_batch(Device.objects.filter(id__in=ids_for_room_status))

    logger.debug(
        "[update_activity_devices_batch] Processed %d device(s), %d updated, %d created, %d debounced",
        len(device_ids),
        len(to_update),
        len(to_create),
        len(skip_devices),
    )

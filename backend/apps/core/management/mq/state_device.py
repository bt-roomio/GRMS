import logging
from collections import defaultdict

from core.management.mq.get_device import get_sub_device
from core.utils.get_time import get_mil_sec
from main.models import Device
from main.observables.device import publish_device
from main.observables.room_status import publish_room_status
from shuttle.models import AttributeKv
from shuttle.services.attribute_kv import publish_updates_attribute_batch
from shuttle.utils.has_changed_and_update import (
    get_cached_attributes,
    invalidate_attributes_cache,
    set_cached_attributes,
)

logger = logging.getLogger(__name__)


def handle_connect_disconnect(device, topic, data):
    device_id = device.get("id")
    logger.debug("Handling %s for device %s", topic, device_id)
    sub_device_name = data.get("device")
    sub = get_sub_device(device, name=sub_device_name, device_type=data.get("type"))
    connected = not topic.endswith("disconnect")

    update_activity_device(sub.get("id"), connected)


def update_activity_device(device_id, connected=True):
    """
    Обновляет состояние активности устройства и время последней активности.

    Функция выполняет следующие действия:
    1. Получает или создает атрибуты 'active' и 'lastActivityTime' для устройства
    2. Обновляет атрибут 'active' (boolean) в соответствии с параметром connected
    3. Обновляет атрибут 'lastActivityTime' (timestamp) текущим временем
    4. Обновляет статус устройства в модели Device, если состояние изменилось
    5. Публикует обновления атрибутов через WebSocket для real-time уведомлений
    6. Публикует обновление статуса комнаты, если устройство изменило статус

    Оптимизации:
    - Использует Redis кеш (TTL 5 сек) для минимизации запросов к БД
    - Кеш инвалидируется автоматически после bulk_update/bulk_create
    - Пропускает обновление, если устройство уже connected и обновление было менее 1 секунды назад
    - Использует bulk_update/bulk_create для эффективной работы с БД
    - Минимизирует количество запросов к БД через select_related и фильтрацию

    Args:
        device_id (UUID): Идентификатор устройства для обновления
        connected (bool): Статус подключения устройства (True - подключено, False - отключено)

    Returns:
        None

    Поведение:
    - Если устройство уже подключено и последнее обновление было менее 1 секунды назад,
      функция завершается досрочно без изменений (debounce механизм)
    - При создании новых атрибутов используется ignore_conflicts=True для предотвращения
      ошибок при конкурентных вызовах
    - Tenant ID определяется из связанных атрибутов или загружается из модели Device
    - WebSocket публикация происходит только при наличии изменений (to_update or to_create)
    """
    logger.debug(f"Params update_activity_device: {device_id, connected}")
    ts_now = get_mil_sec()

    # Попытка получить атрибуты из Redis кеша
    cached_attrs = get_cached_attributes(str(device_id), ["active", "lastActivityTime"], AttributeKv.SERVER_SCOPE)

    # Переменные для хранения данных из кеша (без использования entity)
    cached_tenant_id = None
    cached_device_status = None
    from_cache = False
    attr_map = {}

    if cached_attrs:
        logger.debug(f"Cache hit for device {device_id}")
        from_cache = True
        attr_map = {}

        if "active" in cached_attrs:
            active_data = cached_attrs["active"]
            if "id" not in active_data:
                cached_attrs = None
            else:
                active_attr = AttributeKv(
                    id=active_data["id"],
                    entity_id=device_id,
                    attribute_key="active",
                    attribute_type=AttributeKv.SERVER_SCOPE,
                    bool_v=active_data["bool_v"],
                    last_update_ts=active_data["last_update_ts"],
                )
                # Сохранить tenant_id и status из кеша
                cached_tenant_id = active_data["tenant_id"]
                cached_device_status = active_data.get("status", False)
                attr_map["active"] = active_attr

        if cached_attrs and "lastActivityTime" in cached_attrs:
            last_data = cached_attrs["lastActivityTime"]
            if "id" not in last_data:
                cached_attrs = None
            else:
                last_activity_attr = AttributeKv(
                    id=last_data["id"],
                    entity_id=device_id,
                    attribute_key="lastActivityTime",
                    attribute_type=AttributeKv.SERVER_SCOPE,
                    long_v=last_data["long_v"],
                    last_update_ts=last_data["last_update_ts"],
                )
                # Если tenant_id еще не установлен, взять из lastActivityTime
                if not cached_tenant_id:
                    cached_tenant_id = last_data["tenant_id"]
                attr_map["lastActivityTime"] = last_activity_attr

        if not cached_attrs:
            from_cache = False
            attr_map = {}

    if not from_cache:
        logger.debug(f"Cache miss for device {device_id}, querying DB")
        # Существующий код запроса к БД
        attrs = AttributeKv.objects.filter(
            entity_id=device_id,
            attribute_type=AttributeKv.SERVER_SCOPE,
            attribute_key__in=["active", "lastActivityTime"],
        ).select_related("entity")

        attr_map = {attr.attribute_key: attr for attr in attrs}

    logger.debug(f"attr_map: {attr_map}")

    active_attr = attr_map.get("active")

    if (
        connected and active_attr and active_attr.bool_v == connected and active_attr.last_update_ts > ts_now - 3000
    ):  # 3 sec threshold (debounce mechanism)
        return

    to_update = []
    to_create = []
    device_needs_update = False

    if active_attr:
        if active_attr.bool_v != connected:  #  or active_attr.last_update_ts != ts_now
            active_attr.bool_v = connected
            active_attr.last_update_ts = ts_now  # Manual update (bulk_update bypasses save())
            active_attr.entity_type = "DEVICE"
            to_update.append(active_attr)

        # Проверка статуса устройства (из кеша или из entity)
        current_device_status = (
            cached_device_status
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

    last_activity_attr = attr_map.get("lastActivityTime")
    if last_activity_attr:
        if last_activity_attr.long_v != ts_now:  #  or last_activity_attr.last_update_ts != ts_now
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

    if to_update:
        logger.debug(f"Updating attributes for device {device_id}: {[attr.attribute_key for attr in to_update]}")
        AttributeKv.objects.bulk_update(to_update, fields=["bool_v", "long_v", "last_update_ts", "entity_type"])

    if to_create:
        logger.debug(f"Creating attributes for device {device_id}: {[attr.attribute_key for attr in to_create]}")
        AttributeKv.objects.bulk_create(to_create, ignore_conflicts=True)

    if device_needs_update:
        Device.objects.filter(id=device_id).update(status=connected)
        # Инвалидировать кеш после изменений в БД
        invalidate_attributes_cache(str(device_id), AttributeKv.SERVER_SCOPE)

    if to_update or to_create:
        # Получить tenant_id из кеша или из entity (упрощённая логика)
        if from_cache:
            tenant_id = cached_tenant_id
        elif active_attr:
            tenant_id = active_attr.entity.tenant_id
        elif last_activity_attr:
            tenant_id = last_activity_attr.entity.tenant_id
        else:
            # Редкий случай - атрибуты создаются впервые
            device = Device.objects.get(id=device_id)
            tenant_id = device.tenant_id

        # Подготовить данные для WebSocket и кеша
        updates_by_device = {}
        device_key = f"{device_id}_{tenant_id}"
        updates = []
        cache_data = {}

        # Вычислить актуальный статус устройства для кеша
        current_status = (
            connected
            if device_needs_update
            else (cached_device_status if from_cache else (active_attr.entity.status if active_attr else False))
        )

        # Цикл для создания updates (WebSocket) - только измененные атрибуты
        for attr in to_update + to_create:
            updates.append(
                {
                    "entity": str(device_id),
                    "key_name": attr.attribute_key,
                    "last_update_ts": ts_now,
                    "scope": AttributeKv.SERVER_SCOPE,
                    "value": attr.bool_v if attr.attribute_key == "active" else attr.long_v,
                }
            )

        # Подготовить данные для кеша - ВСЕ атрибуты (не только измененные)
        # Это гарантирует, что при следующем чтении будут доступны оба атрибута
        for attr_key, attr in attr_map.items():
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

        # Публикация WebSocket обновлений
        if updates:
            updates_by_device[device_key] = updates
            publish_updates_attribute_batch(updates_by_device)

        # Обновление Redis кеша (всегда обновляем если есть изменения)
        if cache_data:
            set_cached_attributes(str(device_id), cache_data, AttributeKv.SERVER_SCOPE, ttl=5)
            logger.debug(f"Cache updated for device {device_id}")

    if device_needs_update and active_attr:
        # Для publish_room_status нужен реальный Device объект
        if from_cache:
            # Загрузить Device из БД, так как данные из кеша
            device = Device.objects.get(id=device_id)
            publish_room_status(device)
            publish_device(device)
        else:
            publish_room_status(active_attr.entity)
            publish_device(active_attr.entity)


def update_activity_devices_batch(device_ids: list, connected: bool = True):
    """
    Батч-версия update_activity_device: обрабатывает список device_ids одним проходом
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

    # Шаг 1: Redis кеш по каждому устройству (как в state_device_batch_async)
    for device_id in device_ids:
        cached_attrs = get_cached_attributes(str(device_id), ["active", "lastActivityTime"], AttributeKv.SERVER_SCOPE)

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
        )
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
        for device in Device.objects.filter(id__in=ids_for_room_status):
            publish_room_status(device)
            publish_device(device)

    logger.debug(
        f"[update_activity_devices_batch] Processed {len(device_ids)} device(s), "
        f"{len(to_update)} updated, {len(to_create)} created, {len(skip_devices)} debounced"
    )

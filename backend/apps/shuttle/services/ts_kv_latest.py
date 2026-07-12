import logging
from collections import defaultdict

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from shuttle.utils.has_changed_and_update import has_changed_and_update

logger = logging.getLogger(__name__)

# Целевые каналы для рассылки изменений телеметрии.
# (базовое имя группы, тип-обработчик, scope)
#   scope="device" → группа f"{base}_{device_id}"
#   scope="tenant" → группа f"{base}_{tenant_id}"
GROUP_TARGETS = (
    ("tskv_latest_updates", "ts_kv_latest_activity", "device"),
    ("tskv_updates", "ts_kv_activity", "device"),
    ("room_status", "get_latest_activity", "tenant"),
    ("emergency_status", "get_latest_activity", "tenant"),
)


def publish_updates_batch(updates_by_device: dict[str, list[dict]]):
    """
    Send updates in batches: for each device_id, send only changed data to each group.
    updates_by_device: { device_id: [ {entity, key, ts, bool_v...}, ... ] }
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        raise ValueError("No channel layer")

    group_send = async_to_sync(channel_layer.group_send)
    logger.info("publish_updates_batch: %d device(s)", len(updates_by_device))

    # Апдейты для tenant-групп копим по арендатору, чтобы отправить один group_send
    # на весь батч, а не по одному на каждое устройство (иначе room_status пересчитывает
    # тяжёлые агрегаты из БД N раз, а emergency_status шлёт N сообщений вместо одного).
    tenant_updates: dict[str, list[dict]] = defaultdict(list)

    for device_id_tenant_id, messages in updates_by_device.items():
        device_id, tenant_id = device_id_tenant_id.split("_")
        changed_messages = has_changed_and_update(device_id, messages)
        if not changed_messages:
            logger.debug("device=%s: all %d message(s) filtered by has_changed_and_update", device_id, len(messages))
            continue

        logger.debug(
            "device=%s: %d/%d message(s) changed, sending to groups", device_id, len(changed_messages), len(messages)
        )
        tenant_updates[tenant_id].extend(changed_messages)

        for base, handler_type, scope in GROUP_TARGETS:
            if scope != "device":
                continue
            group_name = f"{base}_{device_id}"
            logger.debug("group_send → group=%s type=%s updates=%d", group_name, handler_type, len(changed_messages))
            group_send(group_name, {"type": handler_type, "updates": changed_messages})

    for tenant_id, changed_messages in tenant_updates.items():
        for base, handler_type, scope in GROUP_TARGETS:
            if scope != "tenant":
                continue
            group_name = f"{base}_{tenant_id}"
            logger.debug("group_send → group=%s type=%s updates=%d", group_name, handler_type, len(changed_messages))
            group_send(group_name, {"type": handler_type, "updates": changed_messages})

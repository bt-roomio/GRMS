"""Async версии функций публикации для использования в асинхронном контексте (mq_async.py)"""

from channels.layers import get_channel_layer

from shuttle.utils.has_changed_and_update import has_changed_attrs


async def publish_updates_attribute_batch_async(updates_by_device: dict[str, list[dict]]):
    """
    Асинхронная версия publish_updates_attribute_batch для использования в async контексте.
    Отправляем пачками: для каждого device_id шлём в каждую группу только изменившиеся данные.
    updates_by_device: { device_id_tenant_id: [ {entity, key, ts, bool_v...}, ... ] }
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        raise ValueError("No channel layer")

    for device_id_tenant_id, messages in updates_by_device.items():
        device_id, tenant_id = device_id_tenant_id.split("_")
        changed_messages = has_changed_attrs(device_id, messages)
        if not changed_messages:
            continue
        payload = {"type": "get_latest_activity", "updates": changed_messages}
        await channel_layer.group_send("attribute_kv_updates", payload)
        await channel_layer.group_send(f"attribute_kv_updates_{tenant_id}", payload)
        await channel_layer.group_send(
            f"emergency_status_{tenant_id}", {"type": "get_latest_activity", "updates": changed_messages}
        )

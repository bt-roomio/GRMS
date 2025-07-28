from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from shuttle.utils.has_changed_and_update import has_changed_attrs


def publish_updates_attribute_batch(updates_by_device: dict[str, list[dict]]):
    """
    Отправляем пачками: для каждого device_id шлём в каждую группу только изменившиеся данные.
    updates_by_device: { device_id: [ {entity, key, ts, bool_v...}, ... ] }
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
        group_name = "attribute_kv_updates"
        async_to_sync(channel_layer.group_send)(group_name, payload)
        async_to_sync(channel_layer.group_send)(
            f"emergency_status_{tenant_id}", {"type": "get_latest_activity", "updates": changed_messages}
        )

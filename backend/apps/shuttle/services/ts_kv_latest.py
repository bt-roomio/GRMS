from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def publish_updates_batch(updates_by_device: dict[int, list[dict]]):
    """
    Отправляем пачками: для каждого device_id шлём в каждую группу один пакет.
    updates_by_device: { device_id: [ {entity, key, ts, bool_v...}, ... ] }
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        raise ValueError("No channel layer")

    for device_id, messages in updates_by_device.items():
        payload = {"type": "get_latest_activity", "updates": messages}
        group_name = f"tskv_latest_updates_{device_id}"
        async_to_sync(channel_layer.group_send)(group_name, payload)

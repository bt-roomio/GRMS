from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

GROUP_SUFFIXES = (
    "tskv_latest_updates",
    "room_status",
    "emergency_status",
)


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
        for suffix in GROUP_SUFFIXES:
            if "tskv_latest_updates" == suffix:
                group_name = f"{suffix}_{device_id}"
            group_name = suffix
            async_to_sync(channel_layer.group_send)(group_name, payload)

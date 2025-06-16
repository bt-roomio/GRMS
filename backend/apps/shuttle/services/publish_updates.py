from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def publish_updates(group: str, action: str, messages):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(group, {"type": action, "updates": messages})

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from main.models import Device


def publish_room_status(instance: Device):
    channel_layer = get_channel_layer()

    if not channel_layer:
        return

    async_to_sync(channel_layer.group_send)(
        f"room_status_{instance.tenant_id}",
        {
            "type": "get_latest_activity",
            "update": {"tenant_id": str(instance.tenant_id)},
        },
    )

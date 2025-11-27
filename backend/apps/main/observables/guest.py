from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from main.models import Guest
from main.serializers.guest import GuestSerializer


def publish_guest_changes(instance: Guest):
    channel_layer = get_channel_layer()

    if not channel_layer:
        return

    async_to_sync(channel_layer.group_send)(
        f"guests_{instance.room_id}",
        {
            "type": "get_activity",
            "update": GuestSerializer(instance).data,
        },
    )

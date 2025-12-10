from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from main.models import Room
from main.serializers.room import RoomDetailWsSerializer


def publish_room_detail_changes(instance: Room):
    channel_layer = get_channel_layer()

    if not channel_layer:
        return

    async_to_sync(channel_layer.group_send)(
        f"room_detail_{instance.id}",
        {
            "type": "get_activity",
            "update": RoomDetailWsSerializer(instance).data,
        },
    )

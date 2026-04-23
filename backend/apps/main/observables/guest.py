from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from main.models import Guest
from main.serializers.guest import GuestSerializer


def publish_guest_changes(instance: Guest, old_room_id=None):
    channel_layer = get_channel_layer()

    if not channel_layer:
        return

    data = GuestSerializer(instance).data

    # Notify current room subscribers
    async_to_sync(channel_layer.group_send)(
        f"guests_{instance.room_id}",
        {"type": "get_activity", "update": data},
    )

    # If room changed, also notify old room subscribers so they can refresh
    if old_room_id and str(old_room_id) != str(instance.room_id):
        async_to_sync(channel_layer.group_send)(
            f"guests_{old_room_id}",
            {"type": "get_activity", "update": data, "old_room_id": str(old_room_id)},
        )

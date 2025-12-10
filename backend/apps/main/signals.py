import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from main.models import Device, Guest, Room
from main.observables.guest import publish_guest_changes
from main.observables.room_detail import publish_room_detail_changes
from main.observables.room_status import publish_room_status
from main.utils.default_state import StateEnum, attribute_room_state
from shuttle.models import AttributeKv

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Device)
def device_post_save(instance: Device, **kwargs):
    publish_room_status(instance)


@receiver(post_save, sender=AttributeKv)
def update_state_of_room_and_status_device(sender, instance, **kwargs):
    if instance.attribute_type == AttributeKv.CLIENT_SCOPE and instance.attribute_key == "scanned_devices":
        AttributeKv.objects.update_or_create(
            attribute_key=instance.attribute_key,
            attribute_type=AttributeKv.SHARED_SCOPE,
            entity_id=instance.entity_id,
            defaults={"json_v": instance.json_v, "entity_type": "DEVICE"},
        )


@receiver(post_save, sender=Guest)
def guest_update(instance: Guest, **kwargs):
    publish_guest_changes(instance)


@receiver(post_save, sender=Room)
def room(instance: Room, **kwargs) -> None:
    """
    Main signal handler - orchestrates room state updates after Room save.

    Performs three operations:
    1. Removes duplicate states from room
    2. Sends WebSocket notification to clients
    3. Updates physical devices via RabbitMQ (only if state field changed)

    Args:
        instance: Room instance that was saved
        **kwargs: Signal kwargs, including 'update_fields' if using update()
    """
    # 1. Remove duplicates
    _remove_duplicate_states(instance)

    # 2. Send WebSocket notification
    _send_room_status_websocket(instance)

    # 3. Update devices via RabbitMQ (only if state changed)
    update_fields = kwargs.get("update_fields", []) or []
    if not (settings.TESTING or settings.DEBUG or "state" not in update_fields):
        _update_room_devices_status(instance)

    publish_room_detail_changes(instance)


def _remove_duplicate_states(room: Room) -> None:
    """
    Remove duplicate states from room state list.

    Updates the room in database with deduplicated state list.

    Args:
        room: Room instance to process
    """
    try:
        Room.objects.filter(id=room.id).update(state=list(set(room.state)))
    except Exception as e:
        logger.error(f"✗ Failed to remove duplicate states for room {room.number}: {e}")


def _send_room_status_websocket(room: Room) -> None:
    """
    Send room status update to WebSocket clients.

    Sends update to all clients subscribed to room_status_{tenant_id} channel.

    Args:
        room: Room instance to send update for
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.warning("Channel layer not configured, skipping WebSocket notification")
            return

        message = {
            "id": str(room.id),
            "room_num": room.number,
            "tenant": str(room.tenant),
        }
        async_to_sync(channel_layer.group_send)(
            f"room_status_{room.tenant_id}", {"type": "get_latest_activity", **message}
        )
    except Exception as e:
        logger.error(f"✗ Failed to send WebSocket notification for room {room.number}: {e}")


def _update_room_devices_status(room: Room) -> None:
    """
    Update physical devices via RabbitMQ based on room state.

    Sends commands to physical devices (door locks, displays, etc.) when
    room state changes between Available and CheckedIn.

    Args:
        room: Room instance to sync devices for
    """
    try:
        channel = connect_to_rabbitmq()

        if Room.Available in room.state:
            attr_device_id_device_name = attribute_room_state(room, StateEnum.CHECK_IN_OUT, False)
            if attr_device_id_device_name:
                send_msg_status_room(channel, *attr_device_id_device_name)

        elif Room.CheckedIn in room.state:
            attr_device_id_device_name = attribute_room_state(room, StateEnum.CHECK_IN_OUT, True)
            if attr_device_id_device_name:
                send_msg_status_room(channel, *attr_device_id_device_name)
    except Exception as e:
        logger.error(f"✗ Failed to update room devices for room {room.number}: {e}")


def send_msg_status_room(channel, attr, device_id, device_name):
    message = {
        "targetDeviceUUID": device_id,
        "topic": "v1/gateway/attributes",
        "data": {"device": device_name, "data": attr},
    }
    send_to_rabbitmq(channel, message, routing_key="fromGRMS")

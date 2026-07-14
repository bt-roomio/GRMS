import logging
import time

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from core.utils.cache import invalidate_quick_cache
from core.utils.helpers import safely_remove
from main.models import Dashboard, Device, DeviceProfile, Guest, PublicSpace, Room, RoomType
from main.observables.device import publish_device
from main.observables.guest import publish_guest_changes
from main.observables.room_detail import publish_room_detail_changes
from main.observables.room_status import publish_room_status
from main.utils.default_state import AttributeConfig, update_room_device_attributes
from shuttle.models import AttributeKv

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Device)
def device_post_save(instance: Device, **kwargs):
    publish_room_status(instance)
    publish_device(instance)
    invalidate_quick_cache("devices", instance.tenant_id)


@receiver(post_delete, sender=Device)
def device_post_delete(instance: Device, **kwargs):
    invalidate_quick_cache("devices", instance.tenant_id)


@receiver([post_save, post_delete], sender=DeviceProfile)
def device_profile_cache_invalidate(instance: DeviceProfile, **kwargs):
    invalidate_quick_cache("device_profiles", instance.tenant_id)


@receiver([post_save, post_delete], sender=Room)
def room_cache_invalidate(instance: Room, **kwargs):
    invalidate_quick_cache("rooms", instance.tenant_id)


@receiver([post_save, post_delete], sender=RoomType)
def room_type_cache_invalidate(instance: RoomType, **kwargs):
    invalidate_quick_cache("room_types", instance.tenant_id)


@receiver([post_save, post_delete], sender=Dashboard)
def dashboard_cache_invalidate(instance: Dashboard, **kwargs):
    invalidate_quick_cache("dashboards", instance.tenant_id)


@receiver([post_save, post_delete], sender=PublicSpace)
def public_space_cache_invalidate(instance: PublicSpace, **kwargs):
    invalidate_quick_cache("public_spaces", instance.tenant_id)


@receiver([post_save, post_delete], sender=Guest)
def guest_cache_invalidate(instance: Guest, **kwargs):
    invalidate_quick_cache("guests", instance.tenant_id)


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

    make_stable_room_state(instance)

    # 2. Send WebSocket notification
    send_room_status_websocket(instance)

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


def make_stable_room_state(room: Room) -> None:
    """
    Control room state based on is_active, is_reservation or no one guests.
    if any (is_active == true and is_reservation == false) then room is checked in

    Uses QuerySet.update() instead of save() to avoid triggering post_save signal recursion.
    """
    active_guests = room.guests.filter(is_active=True, is_reservation=False)

    old_state = list(room.state)
    new_state = list(room.state)

    if active_guests.exists():
        new_state = safely_remove(new_state, Room.Available)
        if Room.CheckedIn not in new_state:
            new_state.append(Room.CheckedIn)
    else:
        new_state = safely_remove(new_state, Room.CheckedIn)

    if not active_guests.exists() and Room.Available not in new_state:
        new_state.append(Room.Available)

    Room.objects.filter(id=room.id).update(state=new_state)
    room.state = new_state

    if old_state != new_state:
        logger.debug(f"Room {room.number} state: {old_state} → {new_state}")


def send_room_status_websocket(room: Room) -> None:
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
        logger.debug(f"✓ Sent WebSocket notification for room {room.number}")
    except Exception as e:
        logger.error(f"✗ Failed to send WebSocket notification for room {room.number}: {e}")


def _get_tenant_general_settings(room: Room) -> dict:
    if isinstance(room.tenant.additional_info, dict):
        return room.tenant.additional_info.get("general_settings", {})
    return {}


def _update_room_devices_status(room: Room) -> None:
    logger.info(f"✓ Updating room attributes for room {room.number}")
    try:
        channel = connect_to_rabbitmq()
        swap_flag = isinstance(room.additional_info, dict) and room.additional_info.get("swap_flag", "") or ""
        is_swap_flag = swap_flag.isdigit() and bool(int(swap_flag))

        g_settings = _get_tenant_general_settings(room)
        check_in_trigger_value = g_settings.get("check_in_trigger_value", 1)
        check_out_trigger_value = g_settings.get("check_out_trigger_value", 1)

        if Room.CheckedIn in room.state:
            attrs = [
                AttributeConfig("Room reservation status", AttributeKv.SHARED_SCOPE, 1),
                AttributeConfig("Check-in trigger", AttributeKv.CLIENT_SCOPE, check_in_trigger_value),
            ]
        elif Room.Available in room.state:
            attrs = [
                AttributeConfig("Room reservation status", AttributeKv.SHARED_SCOPE, 0),
                AttributeConfig("Check-out trigger", AttributeKv.CLIENT_SCOPE, check_out_trigger_value),
            ]
        else:
            return

        logger.info(f"✓ Changing attributes: {attrs}")
        for attr_data, attr_type, device_id, device_name in update_room_device_attributes(room, attrs):
            if not is_swap_flag:
                send_msg_status_room(channel, attr_type, attr_data, device_id, device_name)
    except Exception as e:
        logger.error(f"✗ Failed to update room devices for room {room.number}: {e}")


def send_msg_status_room(channel, attr_type, attr, device_id, device_name):
    message = {
        "targetDeviceUUID": device_id,
        "topic": "v1/gateway/rpc",
        "data": {"device": device_name, "data": {"id": int(time.time()), "method": "setAttribute", "params": attr}},
    }
    if attr_type == AttributeKv.SHARED_SCOPE:
        message["topic"] = "v1/gateway/attributes"
        message["data"]["data"] = attr

    logger.info(f"✓ Sending RPC: {message}")
    send_to_rabbitmq(channel, message, routing_key="fromGRMS")

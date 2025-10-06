from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from main.models import Room
from main.utils.default_state import StateEnum, attribute_room_state
from shuttle.models import AttributeKv


@receiver(post_save, sender=AttributeKv)
def update_state_of_room_and_status_device(sender, instance, **kwargs):
    if instance.attribute_type == AttributeKv.CLIENT_SCOPE and instance.attribute_key == "scanned_devices":
        AttributeKv.objects.update_or_create(
            attribute_key=instance.attribute_key,
            attribute_type=AttributeKv.SHARED_SCOPE,
            entity_id=instance.entity_id,
            defaults={"json_v": instance.json_v, "entity_type": "DEVICE"},
        )


@receiver(post_save, sender=Room)
def check_for_duplicate_state(instance, **kwargs):
    # Disabling duplicate state
    Room.objects.filter(id=instance.id).update(state=list(set(instance.state)))
    update_fields = kwargs.get("update_fields", []) or []

    channel_layer = get_channel_layer()
    if channel_layer is not None:
        message = {
            "id": str(instance.id),
            "room_num": instance.number,
            "tenant": str(instance.tenant),
        }
        async_to_sync(channel_layer.group_send)(f"room_status_{instance.tenant_id}", {"type": "get_latest_activity", **message})

    if settings.TESTING or settings.DEBUG or "state" not in update_fields:
        return

    # Updating AttributeKv CheckedIn and CheckedOut, then sending message
    channel = connect_to_rabbitmq()

    if Room.Available in instance.state:
        attr_device_id_device_name = attribute_room_state(instance, StateEnum.CHECK_IN_OUT, False)
        if attr_device_id_device_name:
            send_msg_status_room(channel, *attr_device_id_device_name)

    elif Room.CheckedIn in instance.state:
        attr_device_id_device_name = attribute_room_state(instance, StateEnum.CHECK_IN_OUT, True)
        if attr_device_id_device_name:
            send_msg_status_room(channel, *attr_device_id_device_name)


def send_msg_status_room(channel, attr, device_id, device_name):
    message = {
        "targetDeviceUUID": device_id,
        "topic": "v1/gateway/attributes",
        "data": {"device": device_name, "data": attr},
    }
    send_to_rabbitmq(channel, message, routing_key="fromGRMS")

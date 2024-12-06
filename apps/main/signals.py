from django.db.models.signals import post_save
from django.dispatch import receiver

from main.models import Device, Room
from main.utils.remove_or_add_state import remove_or_add
from shuttle.models import AttributeKv


@receiver(post_save, sender=Device)
def update_status_of_room(sender, instance, **kwargs):
    if instance.room:
        working_devices = all(Device.objects.filter(room_id=instance.room_id).values_list("status", flat=True))

        instance.room.status = "ON" if working_devices else "OFF"
        instance.room.save()


@receiver(post_save, sender=AttributeKv)
def update_state_of_room_and_status_device(sender, instance, **kwargs):
    devices = Device.objects.filter(id=instance.entity_id)
    if devices:
        for device in devices:
            if instance.attribute_key == "dnd" and device.room:
                remove_or_add(instance.bool_v, device.room, Room.DoNotDisturb)
            if instance.attribute_key == "mur" and device.room:
                remove_or_add(instance.bool_v, device.room, Room.MakeUpRoom)
            if instance.attribute_key == "active" and instance.attribute_type == AttributeKv.SERVER_SCOPE:
                if device.room:
                    device.room.status = Room.ON if instance.bool_v else Room.OFF
                    device.room.save()
                device.status = bool(instance.bool_v)
                device.save()
    if instance.attribute_type == AttributeKv.CLIENT_SCOPE and instance.attribute_key == "scanned_devices":
        AttributeKv.objects.update_or_create(
            attribute_key=instance.attribute_key,
            attribute_type=AttributeKv.SHARED_SCOPE,
            entity_id=instance.entity_id,
            defaults={"json_v": instance.json_v, "entity_type": "DEVICE"},
        )


@receiver(post_save, sender=Room)
def check_for_duplicate_state(instance, **kwargs):
    Room.objects.filter(id=instance.id).update(state=list(set(instance.state)))

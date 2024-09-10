from django.db.models.signals import post_save
from django.dispatch import receiver

from main.models import Device, Room
from shuttle.models import AttributeKv


@receiver(post_save, sender=Device)
def update_status_of_room(sender, instance, **kwargs):
    if instance.room:
        working_devices = all(Device.objects.filter(room_id=instance.room_id).values_list("status", flat=True))

        instance.room.status = "ON" if working_devices else "OFF"
        instance.room.save()


@receiver(post_save, sender=AttributeKv)
def update_state_of_room(sender, instance, **kwargs):
    devices = Device.objects.filter(id=instance.entity_id)
    if devices:
        for device in devices:
            if instance.attribute_key == "dnd":
                device.room.state = Room.DoNotDistrub
                device.room.save()
            if instance.attribute_key == "mur":
                device.room.state = Room.MakeUpRoom
                device.room.save()

from django.db.models.signals import post_save
from django.dispatch import receiver

from main.models import Device


@receiver(post_save, sender=Device)
def update_status_of_room(sender, instance, **kwargs):
    if instance.room:
        working_devices = all(Device.objects.filter(room_id=instance.room_id).values_list("status", flat=True))

        instance.room.status = "ON" if working_devices else "OFF"
        instance.room.save()


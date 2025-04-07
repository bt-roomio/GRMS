from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from shuttle.models import TsKv


@receiver(post_save, sender=TsKv)
def tskv_signal_handler(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)(
            "tskv_updates",
            {
                "type": "tskv.update",
                "instance_id": str(instance.id),
            },
        )

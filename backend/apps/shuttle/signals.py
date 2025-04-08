from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from shuttle.models import TsKv, TsKvLatest


@receiver(post_save, sender=TsKv)
def tskv_signal_handler(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        message = {
            "entity": str(instance.entity_id),
            "key": instance.key.key,
            "ts": instance.ts,
            "bool_v": instance.bool_v,
            "str_v": instance.str_v,
            "long_v": instance.long_v,
            "dbl_v": instance.dbl_v,
            "json_v": instance.json_v,
        }

        async_to_sync(channel_layer.group_send)("tskv_updates", {"type": "get_latest_activity", **message})


@receiver(post_save, sender=TsKvLatest)
def tskv_latest_signal_handler(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        message = {
            "entity": str(instance.entity_id),
            "key": instance.key.key,
            "ts": instance.ts,
            "bool_v": instance.bool_v,
            "str_v": instance.str_v,
            "long_v": instance.long_v,
            "dbl_v": instance.dbl_v,
            "json_v": instance.json_v,
        }
        async_to_sync(channel_layer.group_send)("tskv_latest_updates", {"type": "get_latest_activity", **message})

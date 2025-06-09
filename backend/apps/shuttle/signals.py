from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from shuttle.models import AttributeKv, TsKv, TsKvLatest
from shuttle.utils.has_changed_and_update import has_changed_and_update


@receiver(post_save, sender=TsKv)
def tskv_signal_handler(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        message = {
            "entity": str(instance.entity_id),
            "key": instance.key.key,
            "ts": instance.ts.isoformat(),
            "bool_v": instance.bool_v,
            "str_v": instance.str_v,
            "long_v": instance.long_v,
            "dbl_v": instance.dbl_v,
            "json_v": instance.json_v,
        }

        async_to_sync(channel_layer.group_send)("tskv_updates", {"type": "get_latest_ts_kv_activity", **message})


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
        changed_messages = has_changed_and_update(instance.entity_id, [message])
        if not changed_messages:
            return

        async_to_sync(channel_layer.group_send)(
            f"tskv_latest_updates_{instance.entity_id}", {"type": "ts_kv_latest_activity", "update": message}
        )
        async_to_sync(channel_layer.group_send)("room_status", {"type": "get_latest_activity", **message})
        async_to_sync(channel_layer.group_send)("emergency_status", {"type": "get_latest_activity", **message})


@receiver(post_save, sender=AttributeKv)
def attribute_kv_signal_handler(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        message = {
            "entity": str(instance.entity_id),
            "last_update_ts": instance.last_update_ts,
            "scope": instance.attribute_type,
            "key_name": instance.attribute_key,
            "bool_v": instance.bool_v,
            "str_v": instance.str_v,
            "long_v": instance.long_v,
            "dbl_v": instance.dbl_v,
            "json_v": instance.json_v,
        }
        async_to_sync(channel_layer.group_send)("attribute_kv_updates", {"type": "get_latest_activity", **message})

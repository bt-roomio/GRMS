from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from shuttle.models import AttributeKv, TsKv, TsKvLatest
from shuttle.utils.has_changed_and_update import has_changed_and_update, has_changed_attrs


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

        async_to_sync(channel_layer.group_send)(
            f"tskv_updates_{instance.entity_id}",
            {"type": "ts_kv_activity", "update": message},
        )


@receiver(post_save, sender=TsKvLatest)
def tskv_latest_signal_handler(sender, instance, **kwargs):
    tenant_id = instance.entity.tenant_id
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        fields = ["bool_v", "str_v", "dbl_v", "long_v", "json_v"]
        message = {
            "entity": str(instance.entity_id),
            "key": instance.key.key,
            "ts": instance.ts,
            "bool_v": instance.bool_v,
            "str_v": instance.str_v,
            "long_v": instance.long_v,
            "dbl_v": instance.dbl_v,
            "json_v": instance.json_v,
            "value": next((getattr(instance, field) for field in fields if getattr(instance, field) is not None), None),
        }
        changed_messages = has_changed_and_update(instance.entity_id, [message])
        if not changed_messages:
            return

        async_to_sync(channel_layer.group_send)(
            f"tskv_latest_updates_{instance.entity_id}",
            {"type": "ts_kv_latest_activity", "update": message},
        )
        async_to_sync(channel_layer.group_send)(f"room_status_{tenant_id}", {"type": "get_latest_activity", **message})
        async_to_sync(channel_layer.group_send)(
            f"emergency_status_{tenant_id}", {"type": "get_latest_activity", "update": message}
        )


@receiver(post_save, sender=AttributeKv)
def attribute_kv_signal_handler(sender, instance: AttributeKv, **kwargs):
    fields = ("bool_v", "str_v", "dbl_v", "long_v", "json_v")
    value = next((getattr(instance, f) for f in fields if getattr(instance, f) is not None), None)

    if value is None:
        return

    device_id = str(instance.entity_id)
    tenant_id = getattr(getattr(instance, "entity", None), "tenant_id", None)
    scope = instance.attribute_type
    key_name = instance.attribute_key
    ts_ms = instance.last_update_ts

    message = {
        "entity": device_id,
        "last_update_ts": ts_ms,
        "scope": scope,
        "key_name": key_name,
        "value": value,
    }

    def _publish_after_commit():
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        changed_messages = has_changed_attrs(device_id, [message])
        if not changed_messages:
            return

        async_to_sync(channel_layer.group_send)(
            "attribute_kv_updates", {"type": "get_latest_activity", "update": message}
        )
        async_to_sync(channel_layer.group_send)(
            f"attribute_kv_updates_{instance.entity.tenant_id}", {"type": "get_latest_activity", "update": message}
        )
        async_to_sync(channel_layer.group_send)(
            f"emergency_status_{instance.entity.tenant_id}", {"type": "get_latest_activity", "update": message}
        )

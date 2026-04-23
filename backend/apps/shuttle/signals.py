import asyncio
import threading

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from shuttle.models import AttributeKv, TsKv, TsKvLatest
from shuttle.utils.has_changed_and_update import has_changed_and_update, has_changed_attrs

_local = threading.local()


async def _send_groups(channel_layer, groups_payloads: list[tuple[str, dict]]):
    await asyncio.gather(*[channel_layer.group_send(group, payload) for group, payload in groups_payloads])


def _flush_attribute_kv_batch():
    batch: dict[str, list] | None = getattr(_local, "attr_batch", None)
    _local.attr_batch = None
    if not batch:
        return
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    groups_payloads = []
    for tenant_id, messages in batch.items():
        payload = {"type": "get_latest_activity", "updates": messages}
        groups_payloads.extend(
            [
                ("attribute_kv_updates", payload),
                (f"attribute_kv_updates_{tenant_id}", payload),
                (f"emergency_status_{tenant_id}", {"type": "get_latest_activity", "updates": messages}),
            ]
        )
    async_to_sync(_send_groups)(channel_layer, groups_payloads)


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
    message = {
        "entity": device_id,
        "last_update_ts": instance.last_update_ts,
        "scope": instance.attribute_type,
        "key_name": instance.attribute_key,
        "value": value,
    }

    changed_messages = has_changed_attrs(device_id, [message])
    if not changed_messages:
        return

    tenant_id = str(instance.entity.tenant_id)

    is_new_batch = not hasattr(_local, "attr_batch") or _local.attr_batch is None
    if is_new_batch:
        _local.attr_batch = {}

    _local.attr_batch.setdefault(tenant_id, []).extend(changed_messages)

    if is_new_batch:
        transaction.on_commit(_flush_attribute_kv_batch)

"""Async versions of the publish functions for use in an async context (mq_async.py)"""

import asyncio

from channels.layers import get_channel_layer

from shuttle.utils.has_changed_and_update import has_changed_attrs


async def publish_updates_attribute_batch_async(updates_by_device: dict[str, list[dict]]):
    """
    Async version of publish_updates_attribute_batch for use in an async context.
    Sent in batches: for each device_id, only changed data is sent to each group.
    updates_by_device: { device_id_tenant_id: [ {entity, key, ts, bool_v...}, ... ] }
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        raise ValueError("No channel layer")

    groups_payloads = []
    for device_id_tenant_id, messages in updates_by_device.items():
        device_id, tenant_id = device_id_tenant_id.split("_")
        changed_messages = has_changed_attrs(device_id, messages)
        if not changed_messages:
            continue
        payload = {"type": "get_latest_activity", "updates": changed_messages}
        groups_payloads.extend(
            [
                (f"attribute_kv_updates_{tenant_id}", payload),
                (f"emergency_status_{tenant_id}", {"type": "get_latest_activity", "updates": changed_messages}),
            ]
        )

    if groups_payloads:
        await asyncio.gather(*[channel_layer.group_send(group, payload) for group, payload in groups_payloads])

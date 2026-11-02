import logging
from collections import defaultdict

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from shuttle.utils.has_changed_and_update import has_changed_and_update

logger = logging.getLogger(__name__)

# Target channels for broadcasting telemetry changes.
# (base group name, handler type, scope)
#   scope="device" -> group f"{base}_{device_id}"
#   scope="tenant" -> group f"{base}_{tenant_id}"
GROUP_TARGETS = (
    ("tskv_latest_updates", "ts_kv_latest_activity", "device"),
    ("tskv_updates", "ts_kv_activity", "device"),
    ("room_status", "get_latest_activity", "tenant"),
    ("emergency_status", "get_latest_activity", "tenant"),
)


def publish_updates_batch(updates_by_device: dict[str, list[dict]]):
    """
    Send updates in batches: for each device_id, send only changed data to each group.
    updates_by_device: { device_id: [ {entity, key, ts, bool_v...}, ... ] }
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        raise ValueError("No channel layer")

    logger.info("publish_updates_batch: %d device(s)", len(updates_by_device))

    # Updates for tenant groups are accumulated per tenant to send a single group_send
    # for the whole batch rather than one per device (otherwise room_status recomputes
    # heavy aggregates from the DB N times, and emergency_status sends N messages instead of one).
    tenant_updates: dict[str, list[dict]] = defaultdict(list)
    # Collect all (group, payload) pairs in the sync part and do the fan-out in ONE
    # sync<->async boundary crossing: async_to_sync per group_send costs ~9.4 ms (spinning
    # up the event loop), a serial await in one context ~0.9 ms (10.8x on the dominant cost).
    sends: list[tuple[str, dict]] = []

    for device_id_tenant_id, messages in updates_by_device.items():
        device_id, tenant_id = device_id_tenant_id.split("_")
        changed_messages = has_changed_and_update(device_id, messages)
        if not changed_messages:
            logger.debug("device=%s: all %d message(s) filtered by has_changed_and_update", device_id, len(messages))
            continue

        logger.debug(
            "device=%s: %d/%d message(s) changed, sending to groups", device_id, len(changed_messages), len(messages)
        )
        tenant_updates[tenant_id].extend(changed_messages)

        for base, handler_type, scope in GROUP_TARGETS:
            if scope != "device":
                continue
            sends.append((f"{base}_{device_id}", {"type": handler_type, "updates": changed_messages}))

    for tenant_id, changed_messages in tenant_updates.items():
        for base, handler_type, scope in GROUP_TARGETS:
            if scope != "tenant":
                continue
            sends.append((f"{base}_{tenant_id}", {"type": handler_type, "updates": changed_messages}))

    if not sends:
        return

    async def _fanout():
        for group_name, payload in sends:
            await channel_layer.group_send(group_name, payload)

    logger.debug("publish_updates_batch: fanning out %d group_send(s)", len(sends))
    async_to_sync(_fanout)()

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from shuttle.utils.has_changed_and_update import has_changed_and_update

logger = logging.getLogger(__name__)

GROUP_SUFFIXES = (
    "tskv_latest_updates",
    "tskv_updates",
    "room_status",
    "emergency_status_%s",
)


def publish_updates_batch(updates_by_device: dict[str, list[dict]]):
    """
    Send updates in batches: for each device_id, send only changed data to each group.
    updates_by_device: { device_id: [ {entity, key, ts, bool_v...}, ... ] }
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        raise ValueError("No channel layer")

    suffix_config = {
        "tskv_latest_updates": "ts_kv_latest_activity",
        "tskv_updates": "ts_kv_activity",
        "emergency_status_%s": "get_latest_activity",
    }

    logger.info("publish_updates_batch: %d device(s)", len(updates_by_device))

    for device_id_tenant_id, messages in updates_by_device.items():
        device_id, tenant_id = device_id_tenant_id.split("_")
        changed_messages = has_changed_and_update(device_id, messages)
        if not changed_messages:
            logger.info("device=%s: all %d message(s) filtered by has_changed_and_update", device_id, len(messages))
            continue

        logger.info(
            "device=%s: %d/%d message(s) changed, sending to groups", device_id, len(changed_messages), len(messages)
        )

        for suffix in GROUP_SUFFIXES:
            group_name = (
                f"emergency_status_{tenant_id}"
                if suffix == "emergency_status_%s"
                else f"{suffix}_{device_id}"
                if suffix in suffix_config
                else suffix
            )
            payload = {
                "type": suffix_config.get(suffix, "get_latest_activity"),
                "updates": changed_messages,
            }
            logger.info("group_send → group=%s type=%s updates=%d", group_name, payload["type"], len(changed_messages))
            async_to_sync(channel_layer.group_send)(group_name, payload)

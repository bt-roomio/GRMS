import logging

from core.management.mq.get_device import get_sub_device
from core.utils.get_time import get_mil_sec
from shuttle.models import AttributeKv

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


def handle_connect_disconnect(device, topic, data):
    device_id = device.get("id")
    logger.debug("Handling %s for device %s", topic, device_id)
    sub_device_name = data.get("device")
    sub = get_sub_device(device, name=sub_device_name)
    connected = not topic.endswith("disconnect")

    update_activity_device(sub.get("id"), connected)


def update_activity_device(device_id, connected=True):
    logger.debug(f"Params update_activity_device: {device_id, connected}")
    ts_now = get_mil_sec()

    # Active state and Last activity
    attrs = AttributeKv.objects.filter(
        entity_id=device_id, attribute_type=AttributeKv.SERVER_SCOPE, attribute_key__in=["active", "lastActivityTime"]
    )

    attr_map = {attr.attribute_key: attr for attr in attrs}
    logger.debug(f"attr_map: {attr_map}")

    active_attr = attr_map.get("active")
    # Early exit when no update is required
    if (
        connected and active_attr and active_attr.bool_v == connected and active_attr.last_update_ts > ts_now - 1000
    ):  # 1 sec threshold
        return

    if active_attr:
        if active_attr.bool_v != connected or active_attr.last_update_ts != ts_now:
            active_attr.bool_v = connected
            active_attr.last_update_ts = ts_now
            active_attr.entity_type = "DEVICE"
            active_attr.save()

        # Updating device status
        if not active_attr.entity.status:
            active_attr.entity.status = True
            active_attr.entity.save()
    else:
        AttributeKv.objects.create(
            entity_id=device_id,
            attribute_key="active",
            entity_type="DEVICE",
            attribute_type=AttributeKv.SERVER_SCOPE,
            bool_v=connected,
            last_update_ts=ts_now,
        )

    last_activity_attr = attr_map.get("lastActivityTime")
    if last_activity_attr:
        if last_activity_attr.long_v != ts_now or last_activity_attr.last_update_ts != ts_now:
            last_activity_attr.long_v = ts_now
            last_activity_attr.last_update_ts = ts_now
            last_activity_attr.entity_type = "DEVICE"
            last_activity_attr.save()
    else:
        AttributeKv.objects.create(
            entity_id=device_id,
            attribute_key="lastActivityTime",
            entity_type="DEVICE",
            attribute_type=AttributeKv.SERVER_SCOPE,
            long_v=ts_now,
            last_update_ts=ts_now,
        )

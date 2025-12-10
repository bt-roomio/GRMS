import logging

from core.management.mq.get_device import get_sub_device
from core.utils.get_time import get_mil_sec
from main.models import Device
from main.observables.room_status import publish_room_status
from shuttle.models import AttributeKv
from shuttle.services.attribute_kv import publish_updates_attribute_batch

logger = logging.getLogger(__name__)


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

    attrs = AttributeKv.objects.filter(
        entity_id=device_id, attribute_type=AttributeKv.SERVER_SCOPE, attribute_key__in=["active", "lastActivityTime"]
    ).select_related("entity")

    attr_map = {attr.attribute_key: attr for attr in attrs}
    logger.debug(f"attr_map: {attr_map}")

    active_attr = attr_map.get("active")

    if (
        connected and active_attr and active_attr.bool_v == connected and active_attr.last_update_ts > ts_now - 1000
    ):  # 1 sec threshold
        return

    to_update = []
    to_create = []
    device_needs_update = False

    if active_attr:
        if active_attr.bool_v != connected or active_attr.last_update_ts != ts_now:
            active_attr.bool_v = connected
            active_attr.last_update_ts = ts_now  # Manual update (bulk_update bypasses save())
            active_attr.entity_type = "DEVICE"
            to_update.append(active_attr)

        if active_attr.entity.status != connected:
            device_needs_update = True
    else:
        to_create.append(
            AttributeKv(
                entity_id=device_id,
                attribute_key="active",
                entity_type="DEVICE",
                attribute_type=AttributeKv.SERVER_SCOPE,
                bool_v=connected,
                last_update_ts=ts_now,
            )
        )

    last_activity_attr = attr_map.get("lastActivityTime")
    if last_activity_attr:
        if last_activity_attr.long_v != ts_now or last_activity_attr.last_update_ts != ts_now:
            last_activity_attr.long_v = ts_now
            last_activity_attr.last_update_ts = ts_now
            last_activity_attr.entity_type = "DEVICE"
            to_update.append(last_activity_attr)
    else:
        to_create.append(
            AttributeKv(
                entity_id=device_id,
                attribute_key="lastActivityTime",
                entity_type="DEVICE",
                attribute_type=AttributeKv.SERVER_SCOPE,
                long_v=ts_now,
                last_update_ts=ts_now,
            )
        )

    if to_update:
        AttributeKv.objects.bulk_update(to_update, fields=["bool_v", "long_v", "last_update_ts", "entity_type"])

    if to_create:
        AttributeKv.objects.bulk_create(to_create, ignore_conflicts=True)

    if device_needs_update:
        Device.objects.filter(id=device_id).update(status=connected)

    if to_update or to_create:
        if active_attr:
            tenant_id = active_attr.entity.tenant_id
        elif last_activity_attr:
            tenant_id = last_activity_attr.entity.tenant_id
        else:
            device = Device.objects.get(id=device_id)
            tenant_id = device.tenant_id

        updates_by_device = {}
        device_key = f"{device_id}_{tenant_id}"
        updates = []

        for attr in to_update + to_create:
            updates.append(
                {
                    "entity": str(device_id),
                    "key_name": attr.attribute_key,
                    "last_update_ts": ts_now,
                    "scope": AttributeKv.SERVER_SCOPE,
                    "value": attr.bool_v if attr.attribute_key == "active" else attr.long_v,
                }
            )

        if updates:
            updates_by_device[device_key] = updates
            publish_updates_attribute_batch(updates_by_device)

    if device_needs_update and active_attr:
        publish_room_status(active_attr.entity)

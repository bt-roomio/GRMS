import logging
from uuid import UUID

from django.db import transaction
from django.db.models import F

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from core.utils.get_time import get_mil_sec
from main.models import Device, GlobalSettingsTemplate
from shuttle.models import AttributeKv, Relation
from shuttle.utils.attributes_message import build_attributes_message
from shuttle.utils.find_compatible_field import find_compatible_field

logger = logging.getLogger(__name__)

TEMPLATE_ID_KEY = "template_id"
VALUE_FIELDS = ("bool_v", "str_v", "long_v", "dbl_v", "json_v")


def apply_template(template: GlobalSettingsTemplate, room_ids: list[UUID]) -> list[UUID]:
    """
    Apply a global settings template to the active devices of the given rooms:
    ``config`` goes to SHARED_SCOPE, the template id to SERVER_SCOPE, ``used`` is incremented
    when at least one device received the template.

    Attributes are written with one bulk upsert per call; the websocket publish and the
    RabbitMQ push of the shared attributes run in Celery once the transaction commits.
    """
    from main.tasks import push_shared_attributes_task
    from shuttle.tasks import publish_updates_attribute_batch_task

    devices = list(Device.objects.filter(room_id__in=room_ids, is_active=True).values_list("id", "tenant_id"))
    device_ids = [device_id for device_id, _ in devices]
    shared_fields = find_compatible_field(template.config or {})
    scoped_fields = [
        (AttributeKv.SHARED_SCOPE, shared_fields),
        (AttributeKv.SERVER_SCOPE, find_compatible_field({TEMPLATE_ID_KEY: str(template.id)})),
    ]
    shared = {key: value for key, (_, value) in shared_fields.items()}
    ts = get_mil_sec()

    objects, updates_by_device = [], {}
    for device_id, tenant_id in devices:
        updates = updates_by_device[f"{device_id}_{tenant_id}"] = []
        for scope, fields in scoped_fields:
            for key, (field, value) in fields.items():
                objects.append(_attribute(device_id, scope, key, field, value, ts))
                updates.append(
                    {"entity": str(device_id), "key_name": key, "last_update_ts": ts, "scope": scope, "value": value}
                )

    # Same lock order as the mq-async upserts to avoid deadlocks with them.
    objects.sort(key=lambda attr: (attr.entity_type, attr.attribute_type, str(attr.entity_id), attr.attribute_key))

    if not objects:
        return device_ids

    with transaction.atomic():
        AttributeKv.objects.bulk_create(
            objects,
            update_conflicts=True,
            update_fields=[*VALUE_FIELDS, "last_update_ts"],
            unique_fields=["entity_type", "attribute_type", "entity_id", "attribute_key"],
        )
        GlobalSettingsTemplate.objects.filter(pk=template.pk).update(used=F("used") + 1)

        transaction.on_commit(lambda: publish_updates_attribute_batch_task.delay(updates_by_device))
        if shared:
            ids = [str(device_id) for device_id in device_ids]
            transaction.on_commit(lambda: push_shared_attributes_task.delay(ids, shared))

    return device_ids


def _attribute(device_id: UUID, scope: str, key: str, field: str, value, ts: int) -> AttributeKv:
    values = dict.fromkeys(VALUE_FIELDS) | {field: value}
    return AttributeKv(
        entity_id=device_id,
        entity_type="DEVICE",
        attribute_type=scope,
        attribute_key=key,
        last_update_ts=ts,
        **values,
    )


def push_shared_attributes(device_ids: list[str], attributes: dict) -> None:
    """Push the attributes to every device over a single RabbitMQ connection."""
    devices = Device.objects.filter(id__in=device_ids).only("id", "name", "additional_info")
    gateways: dict = {}
    relations = (
        Relation.objects.filter(to_id_id__in=device_ids, from_id__additional_info__gateway=True)
        .order_by("created_at")
        .values_list("to_id_id", "from_id_id")
    )
    for to_id, from_id in relations:
        gateways.setdefault(to_id, from_id)

    pushed = 0
    channel = connect_to_rabbitmq()
    try:
        for device in devices:
            is_gateway = bool(device.additional_info and device.additional_info.get("gateway"))
            if not is_gateway and device.id not in gateways:
                logger.warning("Device %s has no parent gateway, shared attributes not pushed", device.id)
                continue
            send_to_rabbitmq(channel, build_attributes_message(device, gateways.get(device.id), attributes))
            pushed += 1
    finally:
        channel.connection.close()
    logger.info("Global settings template attributes pushed to %d of %d devices", pushed, len(device_ids))

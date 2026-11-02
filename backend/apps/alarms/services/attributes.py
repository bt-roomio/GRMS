"""
Server-scope attribute helpers.

The per-device notification toggle is a server attribute rather than a column,
which is the ThingsBoard way: the rule reads it as an ordinary condition filter
and no schema changes are needed to add the next toggle.
"""

from typing import Any

from django.db.models import Q

from alarms.constants import ATTR_GATEWAY_ACTIVE
from core.utils.get_time import get_mil_sec
from shuttle.models import AttributeKv

ENTITY_TYPE = "DEVICE"

COLUMN_FOR_TYPE = {
    bool: "bool_v",
    int: "long_v",
    float: "dbl_v",
    str: "str_v",
}


def value_column(value: Any) -> str:
    # bool before int: bool is a subclass of int and would land in long_v.
    return COLUMN_FOR_TYPE.get(type(value), "json_v")


def set_server_attribute(device_id, key: str, value: Any) -> AttributeKv:
    column = value_column(value)
    attribute, _ = AttributeKv.objects.update_or_create(
        entity_type=ENTITY_TYPE,
        attribute_type=AttributeKv.SERVER_SCOPE,
        entity_id=device_id,
        attribute_key=key,
        defaults={column: value, "last_update_ts": get_mil_sec()},
    )
    return attribute


def set_gateway_active(device_ids, value: bool) -> int:
    """
    Mirror a gateway's state onto the devices behind it.

    This is the whole gateway-cascade answer. The watchdog already silences a
    dead gateway's devices, and without this flag the plain offline rule would
    raise one alarm per device — hundreds for a single physical incident. With
    it the rule simply carries one more condition, and the evaluator stays free
    of special cases.
    """
    device_ids = list(device_ids)
    if not device_ids:
        return 0

    now = get_mil_sec()
    scope = {
        "entity_id__in": device_ids,
        "attribute_type": AttributeKv.SERVER_SCOPE,
        "attribute_key": ATTR_GATEWAY_ACTIVE,
    }

    known = set(AttributeKv.objects.filter(**scope).values_list("entity_id", flat=True))
    missing = [
        AttributeKv(
            entity_type=ENTITY_TYPE,
            attribute_type=AttributeKv.SERVER_SCOPE,
            entity_id=device_id,
            attribute_key=ATTR_GATEWAY_ACTIVE,
            bool_v=value,
            last_update_ts=now,
        )
        for device_id in device_ids
        if device_id not in known
    ]
    if missing:
        AttributeKv.objects.bulk_create(missing, ignore_conflicts=True)

    # Only rows that actually differ, so a steady installation writes nothing.
    stale = AttributeKv.objects.filter(**scope).filter(Q(bool_v=not value) | Q(bool_v__isnull=True))
    return len(missing) + stale.update(bool_v=value, last_update_ts=now)


def get_server_attribute(device_id, key: str, default: Any = None) -> Any:
    attribute = AttributeKv.objects.filter(
        entity_id=device_id,
        attribute_type=AttributeKv.SERVER_SCOPE,
        attribute_key=key,
    ).first()
    if attribute is None:
        return default
    value = attribute.get_value
    return default if value is None else value

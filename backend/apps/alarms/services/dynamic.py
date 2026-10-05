"""
``FilterPredicateValue`` resolution: a constant, or an attribute somewhere up
the hierarchy.

This is what makes "35 °C everywhere, 26 in room 512" a configuration change
rather than a code change.
"""

from typing import Any

from alarms.constants import (
    INHERIT_CHAIN,
    SOURCE_CURRENT_DEVICE,
    SOURCE_CURRENT_ROOM,
    SOURCE_CURRENT_TENANT,
)
from alarms.services.snapshot import DataSnapshot, coerce, first_value


def source_value(source_type: str, attribute: str, snapshot: DataSnapshot) -> Any:
    if source_type == SOURCE_CURRENT_DEVICE:
        return first_value(snapshot.attrs.get(attribute))
    if source_type == SOURCE_CURRENT_ROOM:
        return snapshot.room_attrs.get(attribute)
    if source_type == SOURCE_CURRENT_TENANT:
        return snapshot.tenant_attrs.get(attribute)
    return None


def resolve_dynamic(dynamic: dict, snapshot: DataSnapshot) -> Any:
    source_type = dynamic.get("sourceType")
    attribute = dynamic.get("sourceAttribute")
    if not source_type or not attribute:
        return None

    value = source_value(source_type, attribute, snapshot)
    if value is not None or not dynamic.get("inherit"):
        return value

    # Walk device → room → tenant from wherever the source sits.
    try:
        start = INHERIT_CHAIN.index(source_type) + 1
    except ValueError:
        return None

    for parent in INHERIT_CHAIN[start:]:
        value = source_value(parent, attribute, snapshot)
        if value is not None:
            return value

    return None


def resolve_value(predicate_value: dict | None, snapshot: DataSnapshot, value_type: str) -> Any:
    """``dynamicValue`` wins when it resolves; otherwise ``defaultValue``."""
    if not predicate_value:
        return None

    dynamic = predicate_value.get("dynamicValue")
    if dynamic:
        value = resolve_dynamic(dynamic, snapshot)
        if value is not None:
            return coerce(value, value_type)

    return coerce(predicate_value.get("defaultValue"), value_type)

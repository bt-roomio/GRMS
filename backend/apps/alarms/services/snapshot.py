"""
The values one device offers a rule at one tick.

Built once per device per evaluator pass and handed to every rule of its
profile, so a device with twenty rules still costs one row lookup per key.
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from alarms.constants import (
    KEY_ATTRIBUTE,
    KEY_CONSTANT,
    KEY_ENTITY_FIELD,
    KEY_TIME_SERIES,
    VALUE_BOOLEAN,
    VALUE_DATE_TIME,
    VALUE_NUMERIC,
    VALUE_STRING,
)

VALUE_COLUMNS = ("bool_v", "str_v", "dbl_v", "long_v", "json_v")

TRUE_STRINGS = {"true", "1", "yes", "on"}
FALSE_STRINGS = {"false", "0", "no", "off"}


def first_value(row: dict | None) -> Any:
    """The ``get_value`` idiom of TsKvLatest/AttributeKv: first non-null column."""
    if not row:
        return None
    return next((row[column] for column in VALUE_COLUMNS if row.get(column) is not None), None)


def as_numeric(row: dict | None) -> float | None:
    if not row:
        return None
    for column in ("dbl_v", "long_v"):
        if row.get(column) is not None:
            return float(row[column])
    # Some controllers publish numbers as strings; TB coerces the same way.
    return to_float(row.get("str_v"))


def as_boolean(row: dict | None) -> bool | None:
    if not row:
        return None
    if row.get("bool_v") is not None:
        return bool(row["bool_v"])
    return to_bool(row.get("str_v"))


def as_string(row: dict | None) -> str | None:
    if not row:
        return None
    if row.get("str_v") is not None:
        return row["str_v"]
    value = first_value(row)
    return None if value is None else str(value)


def as_date_time(row: dict | None) -> float | None:
    """DATE_TIME is a millisecond epoch, so it compares as a number."""
    return as_numeric(row)


def to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in TRUE_STRINGS:
        return True
    if text in FALSE_STRINGS:
        return False
    return None


TYPED_READERS = {
    VALUE_NUMERIC: as_numeric,
    VALUE_BOOLEAN: as_boolean,
    VALUE_STRING: as_string,
    VALUE_DATE_TIME: as_date_time,
}


@dataclass
class DataSnapshot:
    device_id: UUID
    tenant_id: UUID
    room_id: UUID | None = None
    device_name: str = ""
    room_number: str | None = None

    # ENTITY_FIELD sources, already narrowed to the whitelist.
    fields: dict[str, Any] = field(default_factory=dict)
    # key name -> raw typed-column row
    ts: dict[str, dict] = field(default_factory=dict)
    attrs: dict[str, dict] = field(default_factory=dict)

    # DynamicValue sources above the device. Plain dicts, because in GRMS only
    # devices have an attribute_kv row (see "Отличия GRMS от ThingsBoard").
    room_attrs: dict[str, Any] = field(default_factory=dict)
    tenant_attrs: dict[str, Any] = field(default_factory=dict)

    def row(self, key_type: str, key: str) -> dict | None:
        if key_type == KEY_TIME_SERIES:
            return self.ts.get(key)
        if key_type == KEY_ATTRIBUTE:
            return self.attrs.get(key)
        return None

    def typed(self, key_type: str, key: str, value_type: str, constant: Any = None) -> Any:
        """The value a condition filter compares, read in the filter's valueType."""
        if key_type == KEY_CONSTANT:
            return coerce(constant, value_type)

        if key_type == KEY_ENTITY_FIELD:
            return coerce(self.fields.get(key), value_type)

        return TYPED_READERS[value_type](self.row(key_type, key))

    def raw(self, key: str) -> Any:
        """Whatever the key holds, telemetry first — used by ${placeholders}."""
        if key in self.ts:
            return first_value(self.ts[key])
        if key in self.attrs:
            return first_value(self.attrs[key])
        return self.fields.get(key)


def coerce(value: Any, value_type: str) -> Any:
    """Read a plain Python value (constant, entity field, attribute override) as a type."""
    if value is None:
        return None
    if value_type == VALUE_NUMERIC or value_type == VALUE_DATE_TIME:
        return to_float(value)
    if value_type == VALUE_BOOLEAN:
        return to_bool(value)
    if isinstance(value, (list, tuple)):
        # A STRING IN/NOT_IN threshold is a list; stringifying it here would
        # turn it into "['a', 'b']" and the membership test would never match.
        return list(value)
    return str(value)

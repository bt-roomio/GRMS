"""Builders for the pure-function tests, so no test needs a database."""

from uuid import uuid4

from alarms.services.snapshot import DataSnapshot

TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"


def snapshot(ts=None, attrs=None, fields=None, **kwargs) -> DataSnapshot:
    return DataSnapshot(
        device_id=kwargs.pop("device_id", uuid4()),
        tenant_id=kwargs.pop("tenant_id", TENANT_ID),
        device_name=kwargs.pop("device_name", "Thermostat 101"),
        room_number=kwargs.pop("room_number", "101"),
        fields=fields or {},
        ts={key: row(value) for key, value in (ts or {}).items()},
        attrs={key: row(value) for key, value in (attrs or {}).items()},
        **kwargs,
    )


def row(value) -> dict:
    """A TsKvLatest/AttributeKv row with the value in its natural column."""
    columns = {"bool_v": None, "str_v": None, "long_v": None, "dbl_v": None, "json_v": None}
    if isinstance(value, bool):
        columns["bool_v"] = value
    elif isinstance(value, int):
        columns["long_v"] = value
    elif isinstance(value, float):
        columns["dbl_v"] = value
    elif isinstance(value, str):
        columns["str_v"] = value
    else:
        columns["json_v"] = value
    return columns


def numeric(operation, default=None, dynamic=None):
    value = {"defaultValue": default}
    if dynamic:
        value["dynamicValue"] = dynamic
    return {"type": "NUMERIC", "operation": operation, "value": value}


def boolean(operation, default):
    return {"type": "BOOLEAN", "operation": operation, "value": {"defaultValue": default}}


def string(operation, default, ignore_case=False):
    return {"type": "STRING", "operation": operation, "value": {"defaultValue": default}, "ignoreCase": ignore_case}


def ts_filter(key, value_type, predicate):
    return {"key": {"type": "TIME_SERIES", "key": key}, "valueType": value_type, "predicate": predicate}


def attr_filter(key, value_type, predicate):
    return {"key": {"type": "ATTRIBUTE", "key": key}, "valueType": value_type, "predicate": predicate}

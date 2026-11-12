"""
Writing a GRMS value to a tag: the device first (MQTT RPC), the database only when the device
accepts it. Shared by ``PUT tag`` and the composite writes, which run several in a row.
"""

from typing import NamedTuple

from core.utils.get_time import get_mil_sec
from shuttle.models import AttributeKv
from shuttle.utils.find_compatible_field import find_compatible_field
from shuttle.views.json_rpc import prepare_mqtt_request

VALUE_COLUMNS = ("bool_v", "str_v", "long_v", "dbl_v", "json_v")
RPC_TIMEOUT = 5


class WriteResult(NamedTuple):
    ok: bool
    rpc: dict | None


def tag_key(tag) -> str:
    return tag.attribute_key if isinstance(tag, AttributeKv) else tag.key.key


def storable(tag, value) -> bool:
    """Whether a value has a column to go to; check it before sending anything."""
    return tag_key(tag) in find_compatible_field({tag_key(tag): value})


def rpc_succeeded(rpc) -> bool:
    """Whether a ``prepare_mqtt_request`` result means the device accepted the change.
    A real device response carries a top-level ``success`` flag (see access_manager
    send_rpc), while the timeout sentinel nests ``success: False`` under ``data``."""
    if not isinstance(rpc, dict) or "error" in rpc:
        return False
    data = rpc.get("data")
    if isinstance(data, dict) and "success" in data:
        return bool(data["success"])
    return bool(rpc.get("success"))


def write_tag_value(tag, value) -> WriteResult:
    """Send ``value`` (a GRMS value with a column, see ``storable``) to the tag's device and store
    it once the device accepts it. The tag's ``entity`` (and ``key`` for telemetry) should be
    selected with it."""
    is_attribute = isinstance(tag, AttributeKv)
    key = tag_key(tag)
    method = "setAttribute" if is_attribute else "setTelemetry"
    rpc = prepare_mqtt_request(tag.entity, method, {key: value}, RPC_TIMEOUT)
    if not rpc_succeeded(rpc):
        # Device rejected or did not respond: keep the stored value unchanged.
        return WriteResult(False, rpc)

    field, stored = find_compatible_field({key: value})[key]
    for column in VALUE_COLUMNS:
        setattr(tag, column, None)
    setattr(tag, field, stored)
    if not is_attribute:
        tag.ts = get_mil_sec()  # TsKvLatest.save() does not refresh ts; AttributeKv.save() does
    tag.save()
    return WriteResult(True, rpc)

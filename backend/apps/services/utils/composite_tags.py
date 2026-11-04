"""
Database side of composite mapping: the room's tags as composite inputs, the composite tags of a
room, and the writes of a composite value.

A composite tag is computed per room. When the room has one physical tag named as the rule's
output, the composite value replaces that tag's value; otherwise the room gets a virtual tag with
the stable id ``virtual_tag_id(room, rule id)``. A rule of a ``device`` profile reads its inputs from
that device only, the others from every device of the room.
"""

import hashlib
import logging
from typing import NamedTuple
from uuid import UUID

from services.mapping import composite
from services.mapping.composite import AMBIGUOUS, MISSING
from services.mapping.engine import SKIP, MappingError
from services.serializers.device_tag_types import range_allowed
from services.serializers.tag import UnixMsDateTimeField
from services.utils.tag_write import storable, write_tag_value
from shuttle.models import AttributeKv, TsKvLatest

logger = logging.getLogger(__name__)


def _rule_mask(rule_id: str) -> int:
    return int.from_bytes(hashlib.sha256(f"grms-virtual-tag:{rule_id}".encode()).digest()[:16], "big")


def virtual_tag_id(room_id, rule_id: str) -> str:
    """The id of a room's virtual tag: the room id XOR a hash of the rule id. It stays the same for
    the room and the rule, and ``virtual_tag_room_id`` gets the room back without a search."""
    return str(UUID(int=UUID(str(room_id)).int ^ _rule_mask(rule_id)))


def virtual_tag_room_id(tag_id, rule_id: str) -> UUID:
    """The room a virtual tag id would belong to if it were the tag of ``rule_id``."""
    return UUID(int=UUID(str(tag_id)).int ^ _rule_mask(rule_id))


class InputRow(NamedTuple):
    """A room tag as a composite input, in GRMS form."""

    id: UUID
    entity_id: UUID
    source: str
    tag_name: str
    value: object
    ts: int | None  # Unix milliseconds
    tag_ranges: list | None


# (source, tag name) -> the room's tags of that name, one per device that has it.
InputIndex = dict[tuple[str, str], list[InputRow]]


class Binding(NamedTuple):
    """A composite rule as a room applies it; ``device_id`` limits its inputs to one device."""

    rule: dict
    device_id: UUID | None


class Inputs(NamedTuple):
    values: dict  # alias -> GRMS value
    unavailable: dict  # alias -> missing_input / ambiguous_source
    rows: dict  # alias -> InputRow


def input_index(rows) -> InputIndex:
    index: InputIndex = {}
    for row in rows:
        index.setdefault((row.source, row.tag_name), []).append(row)
    return index


def _candidates(index: InputIndex, source: str, tag_name: str, device_id) -> list[InputRow]:
    rows = index.get((source, tag_name), [])
    return [row for row in rows if row.entity_id == device_id] if device_id else rows


def read_inputs(binding: Binding, index: InputIndex) -> Inputs:
    """The current values of the rule's inputs; an input with no tag, no value, several tags or a
    goes to ``unavailable``."""
    rule = binding.rule
    values, unavailable, rows = {}, {}, {}
    for item in rule["inputs"]:
        alias = item["alias"]
        found = _candidates(index, item["source"], item["tag_name"], binding.device_id)
        if len(found) > 1:
            unavailable[alias] = AMBIGUOUS
            continue
        if not found or found[0].value is None:
            unavailable[alias] = MISSING
            continue
        row = rows[alias] = found[0]
        values[alias] = row.value
    return Inputs(values, unavailable, rows)


def has_inputs(binding: Binding, index: InputIndex) -> bool:
    """Whether the room has any tag the rule reads: a room with none gets no virtual tag."""
    return any(
        _candidates(index, item["source"], item["tag_name"], binding.device_id) for item in binding.rule["inputs"]
    )


def evaluate(binding: Binding, inputs: Inputs):
    """The integrator value of the inputs; ``None`` when the rule skips them or cannot convert them."""
    try:
        value = composite.to_external(binding.rule, inputs.values, inputs.unavailable)
    except MappingError as exc:
        if exc.code != "direction":
            logger.warning("Composite rule %r: %s", binding.rule["id"], exc)
        return None
    return None if value is SKIP else value


def composite_fields(binding: Binding, index: InputIndex) -> dict:
    """``value``, ``updated_at`` (the latest of the inputs read), ``tag_ranges`` and ``tag_type``
    of the rule's output, in the integrator's form."""
    inputs = read_inputs(binding, index)
    stamps = [row.ts for row in inputs.rows.values() if row.ts is not None]
    output = binding.rule["output"]
    return {
        "value": evaluate(binding, inputs),
        "updated_at": UnixMsDateTimeField().to_representation(max(stamps)) if stamps else None,
        "tag_type": output.get("tag_type"),
        "tag_ranges": composite.output_ranges(binding.rule),
    }


def plan_writes(binding: Binding, index: InputIndex, value):
    """The writes of an integrator value, each with the ``tag_id`` and ``device`` it goes to, or
    ``SKIP``. Every write is checked before anything is sent: its tag is in the room once and its
    value is allowed by the tag's ``tag_ranges``. Raises ``MappingError``."""
    writes = composite.to_grms(binding.rule, value)
    if writes is SKIP:
        return SKIP
    for write in writes:
        alias, name = write["alias"], write["tag_name"]
        found = _candidates(index, write["source"], name, binding.device_id)
        if not found:
            raise MappingError(f"The room has no {write['source']} {name!r} to write.", MISSING, f"inputs.{alias}")
        if len(found) > 1:
            raise MappingError(
                f"Several devices of the room report {write['source']} {name!r}.", AMBIGUOUS, f"inputs.{alias}"
            )
        row = found[0]
        if row.tag_ranges is not None and not range_allowed(write["value"], row.tag_ranges):
            raise MappingError(
                f"{write['value']!r} is not allowed by the tag ranges {row.tag_ranges} of {name!r}.",
                "invalid",
                f"set.{alias}",
            )
        write.update(tag_id=str(row.id), device=str(row.entity_id))
    return writes


def _load_tags(writes) -> dict[str, object]:
    ids = [write["tag_id"] for write in writes]
    tags = {str(pk): tag for pk, tag in AttributeKv.objects.select_related("entity").in_bulk(ids).items()}
    telemetry = TsKvLatest.objects.select_related("entity", "key").in_bulk(ids)
    tags.update({str(pk): tag for pk, tag in telemetry.items()})
    return tags


def execute_writes(writes) -> tuple[bool, list[dict]]:
    """Run the planned writes in order, each waiting for its device. A failed ``required`` write
    stops the rest (``not_run``); a failed optional one does not. Returns whether every required
    write succeeded and each write with its ``status`` (``ok``, ``failed``, ``not_run``) and ``rpc``.
    Raises ``MappingError`` before sending anything when a value has no column to go to."""
    tags = _load_tags(writes)
    for write in writes:
        tag = tags.get(write["tag_id"])
        if tag is None:
            raise MappingError(f"Tag {write['tag_name']!r} is gone.", MISSING, f"inputs.{write['alias']}")
        if not storable(tag, write["value"]):
            raise MappingError(f"Unsupported value type: {type(write['value']).__name__}.", "type", "set")
    stopped, results = False, []
    for write in writes:
        if stopped:
            results.append({**write, "status": "not_run", "rpc": None})
            continue
        result = write_tag_value(tags[write["tag_id"]], write["value"])
        results.append({**write, "status": "ok" if result.ok else "failed", "rpc": result.rpc})
        if not result.ok and write["required"]:
            stopped = True
    return not stopped, results

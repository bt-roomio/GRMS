"""
Value Mapping Engine: converts a tag value between its GRMS form and an integrator's form.

A rule is a plain dict (one per ``TagType`` in an integrator profile, see ``validate_rule``)::

    {"id": "fan_speed", "tag_type": "FCUSPEED", "external": {"value_type": "integer"},
     "direction": "both", "on_invalid": "reject",
     "transform": {"type": "enum", "map": [{"grms": "Low", "external": 1}, ...]}}

``to_external`` runs on reads (tag list, tag detail), ``to_grms`` on writes (``PUT tag``),
``ranges_to_external`` turns the tag's ``tag_ranges`` into values the integrator may send.
No database access: the caller passes the rule (after ``apply_overrides``) and the tag's ranges.
"""

import math
from typing import Any

from services.mapping.constants import (
    NUMERIC_VALUE_TYPES,
    RULE_IDENTITY_FIELDS,
    Direction,
    LinearOp,
    OnInvalid,
    TransformType,
    ValueType,
)
from services.serializers.device_tag_types import is_numeric_range, numeric_bounds, range_allowed
from services.serializers.tag_type import range_value_key

LINEAR_FORWARD = {
    LinearOp.MULTIPLY: lambda value, operand: value * operand,
    LinearOp.DIVIDE: lambda value, operand: value / operand,
    LinearOp.ADD: lambda value, operand: value + operand,
    LinearOp.SUBTRACT: lambda value, operand: value - operand,
}
LINEAR_INVERSE = {
    LinearOp.MULTIPLY: LinearOp.DIVIDE,
    LinearOp.DIVIDE: LinearOp.MULTIPLY,
    LinearOp.ADD: LinearOp.SUBTRACT,
    LinearOp.SUBTRACT: LinearOp.ADD,
}


class MappingError(ValueError):
    """A value the rule cannot convert. ``code`` is ``type`` (wrong JSON type), ``direction``
    (the rule does not convert this way), ``unmapped`` (no enum pair) or ``invalid`` (failed
    validation under ``on_invalid: reject``)."""

    def __init__(self, message: str, code: str = "invalid"):
        super().__init__(message)
        self.code = code


class _Skip:
    def __repr__(self):
        return "SKIP"


# Returned by ``to_grms`` for an invalid value under ``on_invalid: skip``: nothing is written.
SKIP = _Skip()


class _Invalid(Exception):
    """Internal: a value failed validation; ``to_grms`` resolves it by ``on_invalid``."""


def value_key(value) -> str:
    """Identity of a value for enum and ``allowed`` lookups. Types stay apart (``true``, ``1``
    and ``"1"`` differ), but an integral float equals its int: ``dbl_v`` 1.0 matches ``1``."""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return range_value_key(value)


def is_number(value) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def normalize_number(value: float) -> int | float:
    """Drop float noise and return an int for an integral result: 59.99999999 -> 60."""
    value = round(value, 9)
    return int(value) if float(value).is_integer() else value


def round_half_up(value: float) -> int:
    return math.floor(value + 0.5)


def snap(value: float, origin: float, step: float) -> int | float:
    """The nearest point of the grid ``origin + k * step``; a half step rounds up (55 -> 60)."""
    return normalize_number(origin + round_half_up((value - origin) / step) * step)


def coerce(value, value_type: str):
    """An incoming integrator value as ``value_type``. Strings are parsed (``"55"`` is 55,
    ``"true"`` is ``True``), so a value from a query string converts like a JSON one."""
    if value_type == ValueType.BOOLEAN:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().lower() in ("true", "false"):
            return value.strip().lower() == "true"
    elif value_type in NUMERIC_VALUE_TYPES:
        if isinstance(value, str):
            try:
                value = float(value.strip())
            except ValueError:
                value = None
        if is_number(value):
            if value_type == ValueType.NUMBER:
                return normalize_number(value)
            if float(value).is_integer():
                return int(value)
    elif value_type == ValueType.STRING and isinstance(value, str):
        return value
    raise MappingError(f"Expected {value_type}, got {value!r}.", "type")


def cast(value, value_type: str):
    """A computed number in the integrator's numeric ``value_type``."""
    if value_type == ValueType.INTEGER:
        return round_half_up(value)
    return normalize_number(value)


def applies(rule: dict, direction: str) -> bool:
    return rule.get("direction", Direction.BOTH) in (Direction.BOTH, direction)


def apply_overrides(rule: dict, overrides) -> dict:
    """The rule with level overrides applied, from the least specific (tenant) to the most
    specific (device). Each override replaces whole top-level fields, except ``id`` and ``tag_type``."""
    merged = dict(rule)
    for override in overrides:
        merged.update({key: value for key, value in (override or {}).items() if key not in RULE_IDENTITY_FIELDS})
    return merged


def _lookup(pairs, source: str, target: str, value) -> tuple[bool, Any]:
    key = value_key(value)
    for pair in pairs:
        if value_key(pair[source]) == key:
            return True, pair[target]
    return False, None


def _range_forward(transform: dict, value: float) -> float:
    grms, external = transform["grms"], transform["external"]
    value = min(max(value, grms["min"]), grms["max"])
    ratio = (value - grms["min"]) / (grms["max"] - grms["min"])
    if transform.get("invert"):
        ratio = 1 - ratio
    result = external["min"] + ratio * (external["max"] - external["min"])
    if external.get("step"):
        result = snap(result, external["min"], external["step"])
    return min(max(result, external["min"]), external["max"])


def _range_backward(transform: dict, value: float) -> float:
    grms, external = transform["grms"], transform["external"]
    ratio = (value - external["min"]) / (external["max"] - external["min"])
    if transform.get("invert"):
        ratio = 1 - ratio
    result = grms["min"] + ratio * (grms["max"] - grms["min"])
    if grms.get("step"):
        result = snap(result, grms["min"], grms["step"])
    return min(max(result, grms["min"]), grms["max"])


def _linear(ops, value: float, backward: bool = False) -> float:
    steps = reversed(ops) if backward else ops
    for step in steps:
        op = LINEAR_INVERSE[step["op"]] if backward else step["op"]
        value = LINEAR_FORWARD[op](value, step["value"])
    return value


def _numeric_forward(transform: dict, value: float) -> float:
    kind = transform["type"]
    if kind == TransformType.RANGE:
        return _range_forward(transform, value)
    if kind == TransformType.LINEAR:
        return _linear(transform["ops"], value)
    return value


def to_external(rule: dict, value):
    """GRMS value -> integrator value. ``None`` (no value yet) stays ``None``; a rule that does
    not convert reads leaves the value as it is."""
    if value is None or not applies(rule, Direction.TO_EXTERNAL):
        return value
    transform, value_type = rule["transform"], rule["external"]["value_type"]
    kind = transform["type"]
    if kind == TransformType.ENUM:
        found, result = _lookup(transform["map"], "grms", "external", value)
        if not found:
            raise MappingError(f"No enum pair for GRMS value {value!r}.", "unmapped")
        return result
    if kind == TransformType.PASSTHROUGH:
        return coerce(value, value_type)
    value = coerce(value, ValueType.NUMBER)  # a device may store a number as a string
    return cast(_numeric_forward(transform, value), value_type)


def _resolve_number(value, low, high, on_invalid: str):
    """``value`` if within ``[low, high]`` (either bound may be ``None``), clamped under ``clamp``."""
    if (low is None or value >= low) and (high is None or value <= high):
        return value
    if on_invalid != OnInvalid.CLAMP:
        raise _Invalid(f"{value} is outside {low}..{high}.")
    return normalize_number(low if low is not None and value < low else high)


def _check_external(rule: dict, value, on_invalid: str):
    """Validate an incoming value against ``validate`` and, for ``range``, the external bounds.
    A range value is always snapped to the external step: 55 with step 10 becomes 60."""
    limits = rule.get("validate") or {}
    if "allowed" in limits and value_key(value) not in {value_key(item) for item in limits["allowed"]}:
        raise _Invalid(f"{value!r} is not one of {limits['allowed']}.")
    if not is_number(value):
        return value
    low, high = limits.get("min"), limits.get("max")
    transform = rule["transform"]
    if transform["type"] == TransformType.RANGE:
        external = transform["external"]
        low = external["min"] if low is None else max(low, external["min"])
        high = external["max"] if high is None else min(high, external["max"])
        if external.get("step"):
            value = snap(value, external["min"], external["step"])
    if step := limits.get("step"):
        origin = low if low is not None else 0
        snapped = snap(value, origin, step)
        if snapped != value:
            if on_invalid != OnInvalid.CLAMP:
                raise _Invalid(f"{value} is not a multiple of {step}.")
            value = snapped
    return _resolve_number(value, low, high, on_invalid)


def _check_grms(value, tag_ranges, on_invalid: str):
    """Validate a converted value against the tag's ``tag_ranges``; under ``clamp`` a number moves
    to the nearest point of the nearest numeric range."""
    if tag_ranges is None or range_allowed(value, tag_ranges):
        return value
    bounds = [b for b in (numeric_bounds(r) for r in tag_ranges) if b] if is_number(value) else []
    if on_invalid != OnInvalid.CLAMP or not bounds:
        raise _Invalid(f"{value!r} is not allowed by the tag ranges {tag_ranges}.")
    candidates = [min(max(value, low), high) for low, high in bounds]
    return normalize_number(min(candidates, key=lambda candidate: abs(candidate - value)))


def to_grms(rule: dict, value, tag_ranges=None):
    """Integrator value -> GRMS value to write. ``tag_ranges`` (the tag's ranges from its device's
    ``TAG_TYPES``) is checked when given. Returns ``SKIP`` for an invalid value under
    ``on_invalid: skip``; raises ``MappingError`` otherwise."""
    if not applies(rule, Direction.TO_GRMS):
        raise MappingError(f"Rule {rule.get('id')!r} does not accept writes.", "direction")
    transform, value_type = rule["transform"], rule["external"]["value_type"]
    on_invalid = rule.get("on_invalid", OnInvalid.REJECT)
    value = coerce(value, value_type)
    try:
        value = _check_external(rule, value, on_invalid)
        kind = transform["type"]
        if kind == TransformType.ENUM:
            found, value = _lookup(transform["map"], "external", "grms", value)
            if not found:
                raise _Invalid("No enum pair for the value.")
        elif kind == TransformType.RANGE:
            value = normalize_number(_range_backward(transform, value))
        elif kind == TransformType.LINEAR:
            value = normalize_number(_linear(transform["ops"], value, backward=True))
        return _check_grms(value, tag_ranges, on_invalid)
    except _Invalid as exc:
        if on_invalid == OnInvalid.SKIP:
            return SKIP
        raise MappingError(str(exc), "unmapped" if transform["type"] == TransformType.ENUM else "invalid") from None


def _format_bound(value: float) -> str:
    return str(normalize_number(value))


def ranges_to_external(rule: dict, tag_ranges):
    """The tag's ``tag_ranges`` as integrator values, so the integrator sees what it may send.
    Unmappable values are dropped; numeric ranges (``"0-255"``) keep the ``"low-high"`` form.
    Applied whatever the rule's direction: the ranges describe writes as much as reads."""
    if tag_ranges is None:
        return None
    transform, value_type = rule["transform"], rule["external"]["value_type"]
    kind = transform["type"]
    result = []
    for item in tag_ranges:
        if kind == TransformType.ENUM:
            found, converted = _lookup(transform["map"], "grms", "external", item)
            if found:
                result.append(converted)
            continue
        bounds = numeric_bounds(item)
        if bounds is None:
            if kind == TransformType.PASSTHROUGH:
                result.append(item)
            continue
        if is_numeric_range(item):
            low, high = sorted(normalize_number(_numeric_forward(transform, bound)) for bound in bounds)
            if value_type == ValueType.INTEGER:
                # Only the integers within the range: the integrator may send no other value.
                low, high = math.ceil(low), math.floor(high)
                if low > high:
                    continue
            result.append(f"{_format_bound(low)}-{_format_bound(high)}")
        else:
            result.append(cast(_numeric_forward(transform, bounds[0]), value_type))
    seen, unique = set(), []
    for item in result:
        if value_key(item) not in seen:
            seen.add(value_key(item))
            unique.append(item)
    return unique

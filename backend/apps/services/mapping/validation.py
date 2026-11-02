"""
Structural checks of a mapping rule, run before it is saved. They guarantee the engine never
meets a malformed rule: ``min < max``, ``step > 0``, no division by zero, an enum that converts
back and forth unambiguously.
"""

from services.mapping.constants import (
    NUMERIC_TRANSFORMS,
    NUMERIC_VALUE_TYPES,
    Direction,
    LinearOp,
    OnInvalid,
    TransformType,
    ValueType,
)
from services.mapping.engine import is_number, value_key


def matches_value_type(value, value_type: str) -> bool:
    if value_type == ValueType.BOOLEAN:
        return isinstance(value, bool)
    if value_type == ValueType.STRING:
        return isinstance(value, str)
    if value_type == ValueType.INTEGER:
        return is_number(value) and float(value).is_integer()
    return is_number(value)


def _bounds_errors(bounds, label: str, step_required: bool = False) -> list[str]:
    if not isinstance(bounds, dict):
        return [f"{label} must be an object with min and max."]
    errors = []
    low, high, step = bounds.get("min"), bounds.get("max"), bounds.get("step")
    if not is_number(low) or not is_number(high):
        errors.append(f"{label}.min and {label}.max must be numbers.")
    elif low >= high:
        errors.append(f"{label}.min must be less than {label}.max.")
    if step is not None or step_required:
        if not is_number(step) or step <= 0:
            errors.append(f"{label}.step must be a positive number.")
    return errors


def _duplicates(values) -> list:
    seen, duplicates = set(), []
    for value in values:
        key = value_key(value)
        if key in seen:
            duplicates.append(value)
        seen.add(key)
    return duplicates


def _enum_errors(transform: dict, value_type: str, direction: str) -> list[str]:
    pairs = transform.get("map")
    if not isinstance(pairs, list) or not pairs:
        return ["transform.map must be a non-empty list."]
    if not all(isinstance(pair, dict) and "grms" in pair and "external" in pair for pair in pairs):
        return ["Each transform.map item must have grms and external."]
    errors = []
    wrong = [pair["external"] for pair in pairs if not matches_value_type(pair["external"], value_type)]
    if wrong:
        errors.append(f"External values {wrong} are not {value_type}.")
    # Reads look pairs up by the GRMS value, writes by the external one: each must be unique.
    if direction in (Direction.BOTH, Direction.TO_EXTERNAL) and (dup := _duplicates(p["grms"] for p in pairs)):
        errors.append(f"Duplicate GRMS values {dup}: a read would be ambiguous.")
    if direction in (Direction.BOTH, Direction.TO_GRMS) and (dup := _duplicates(p["external"] for p in pairs)):
        errors.append(f"Duplicate external values {dup}: a write would be ambiguous.")
    return errors


def _linear_errors(transform: dict) -> list[str]:
    ops = transform.get("ops")
    if not isinstance(ops, list) or not ops:
        return ["transform.ops must be a non-empty list."]
    errors = []
    for index, step in enumerate(ops):
        if not isinstance(step, dict) or step.get("op") not in LinearOp.values:
            errors.append(f"transform.ops[{index}].op must be one of {LinearOp.values}.")
        elif not is_number(step.get("value")):
            errors.append(f"transform.ops[{index}].value must be a number.")
        elif step["op"] in (LinearOp.MULTIPLY, LinearOp.DIVIDE) and step["value"] == 0:
            # multiply by 0 has no inverse, divide by 0 has no result
            errors.append(f"transform.ops[{index}]: {step['op']} by 0 is not allowed.")
    return errors


def _transform_errors(transform, value_type: str, direction: str) -> list[str]:
    if not isinstance(transform, dict) or transform.get("type") not in TransformType.values:
        return [f"transform.type must be one of {TransformType.values}."]
    kind = transform["type"]
    if kind in NUMERIC_TRANSFORMS and value_type not in NUMERIC_VALUE_TYPES:
        return [f"A {kind} transform needs a numeric external value_type."]
    if kind == TransformType.ENUM:
        return _enum_errors(transform, value_type, direction)
    if kind == TransformType.RANGE:
        errors = _bounds_errors(transform.get("grms"), "transform.grms")
        errors += _bounds_errors(transform.get("external"), "transform.external")
        if "invert" in transform and not isinstance(transform["invert"], bool):
            errors.append("transform.invert must be a boolean.")
        return errors
    if kind == TransformType.LINEAR:
        return _linear_errors(transform)
    return []


def rule_errors(rule) -> list[str]:
    """Every problem of a rule; an empty list means the engine can run it."""
    if not isinstance(rule, dict):
        return ["A rule must be an object."]
    errors = []
    if not isinstance(rule.get("tag_name"), str) or not rule["tag_name"].strip():
        errors.append("tag_name must be a non-empty string.")
    external = rule.get("external")
    value_type = external.get("value_type") if isinstance(external, dict) else None
    if value_type not in ValueType.values:
        errors.append(f"external.value_type must be one of {ValueType.values}.")
    direction = rule.get("direction", Direction.BOTH)
    if direction not in Direction.values:
        errors.append(f"direction must be one of {Direction.values}.")
    on_invalid = rule.get("on_invalid", OnInvalid.REJECT)
    if on_invalid not in OnInvalid.values:
        errors.append(f"on_invalid must be one of {OnInvalid.values}.")
    if errors:  # the checks below rely on value_type and direction
        return errors
    if on_invalid == OnInvalid.CLAMP and value_type not in NUMERIC_VALUE_TYPES:
        errors.append("on_invalid clamp needs a numeric value_type.")
    if on_invalid == OnInvalid.CONST and rule.get("on_invalid_value") is None:
        errors.append("on_invalid const needs on_invalid_value.")
    elif on_invalid != OnInvalid.CONST and rule.get("on_invalid_value") is not None:
        errors.append("on_invalid_value is used only with on_invalid const.")
    errors += _transform_errors(rule.get("transform"), value_type, direction)
    return errors

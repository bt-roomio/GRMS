"""
Structural checks of a mapping rule, run before it is saved. They guarantee the engine never
meets a malformed rule: ``min < max``, ``step > 0``, no division by zero, an enum that converts
back and forth unambiguously.

``rule_issues`` returns each problem with the path of the field it is about (``transform.map``),
so a form can show it next to that field; ``rule_errors`` returns the messages alone.
"""

from typing import NamedTuple

from services.mapping.constants import (
    NUMERIC_TRANSFORMS,
    NUMERIC_VALUE_TYPES,
    TAG_NAME_MAX_LENGTH,
    Direction,
    LinearOp,
    OnInvalid,
    TransformType,
    ValueType,
)
from services.mapping.engine import is_number, value_key


class Issue(NamedTuple):
    """A problem of a rule: ``field`` is the dotted path within the rule (empty for the whole rule),
    ``code`` its kind (``config`` for a malformed rule, ``conflict`` for conditions that overlap)."""

    field: str
    message: str
    code: str = "config"

    def as_dict(self) -> dict:
        return {"field": self.field, "code": self.code, "message": self.message}


def matches_value_type(value, value_type: str) -> bool:
    if value_type == ValueType.BOOLEAN:
        return isinstance(value, bool)
    if value_type == ValueType.STRING:
        return isinstance(value, str)
    if value_type == ValueType.INTEGER:
        return is_number(value) and float(value).is_integer()
    return is_number(value)


def _bounds_issues(bounds, label: str, step_required: bool = False) -> list[Issue]:
    if not isinstance(bounds, dict):
        return [Issue(label, f"{label} must be an object with min and max.")]
    issues = []
    low, high, step = bounds.get("min"), bounds.get("max"), bounds.get("step")
    if not is_number(low) or not is_number(high):
        issues.append(Issue(label, f"{label}.min and {label}.max must be numbers."))
    elif low >= high:
        issues.append(Issue(f"{label}.min", f"{label}.min must be less than {label}.max."))
    if step is not None or step_required:
        if not is_number(step) or step <= 0:
            issues.append(Issue(f"{label}.step", f"{label}.step must be a positive number."))
    return issues


def duplicates(values) -> list:
    seen, repeated = set(), []
    for value in values:
        key = value_key(value)
        if key in seen:
            repeated.append(value)
        seen.add(key)
    return repeated


def _enum_issues(transform: dict, value_type: str, direction: str) -> list[Issue]:
    pairs = transform.get("map")
    if not isinstance(pairs, list) or not pairs:
        return [Issue("transform.map", "transform.map must be a non-empty list.")]
    if not all(isinstance(pair, dict) and "grms" in pair and "external" in pair for pair in pairs):
        return [Issue("transform.map", "Each transform.map item must have grms and external.")]
    issues = []
    wrong = [pair["external"] for pair in pairs if not matches_value_type(pair["external"], value_type)]
    if wrong:
        issues.append(Issue("transform.map", f"External values {wrong} are not {value_type}."))
    # Reads look pairs up by the GRMS value, writes by the external one: each must be unique.
    if direction in (Direction.BOTH, Direction.TO_EXTERNAL) and (dup := duplicates(p["grms"] for p in pairs)):
        issues.append(Issue("transform.map", f"Duplicate GRMS values {dup}: a read would be ambiguous."))
    if direction in (Direction.BOTH, Direction.TO_GRMS) and (dup := duplicates(p["external"] for p in pairs)):
        issues.append(Issue("transform.map", f"Duplicate external values {dup}: a write would be ambiguous."))
    return issues


def _linear_issues(transform: dict) -> list[Issue]:
    ops = transform.get("ops")
    if not isinstance(ops, list) or not ops:
        return [Issue("transform.ops", "transform.ops must be a non-empty list.")]
    issues = []
    for index, step in enumerate(ops):
        field = f"transform.ops[{index}]"
        if not isinstance(step, dict) or step.get("op") not in LinearOp.values:
            issues.append(Issue(f"{field}.op", f"{field}.op must be one of {LinearOp.values}."))
        elif not is_number(step.get("value")):
            issues.append(Issue(f"{field}.value", f"{field}.value must be a number."))
        elif step["op"] in (LinearOp.MULTIPLY, LinearOp.DIVIDE) and step["value"] == 0:
            # multiply by 0 has no inverse, divide by 0 has no result
            issues.append(Issue(f"{field}.value", f"{field}: {step['op']} by 0 is not allowed."))
    return issues


def _transform_issues(transform, value_type: str, direction: str) -> list[Issue]:
    if not isinstance(transform, dict) or transform.get("type") not in TransformType.values:
        return [Issue("transform.type", f"transform.type must be one of {TransformType.values}.")]
    kind = transform["type"]
    if kind in NUMERIC_TRANSFORMS and value_type not in NUMERIC_VALUE_TYPES:
        return [Issue("transform.type", f"A {kind} transform needs a numeric external value_type.")]
    if kind == TransformType.ENUM:
        return _enum_issues(transform, value_type, direction)
    if kind == TransformType.RANGE:
        issues = _bounds_issues(transform.get("grms"), "transform.grms")
        issues += _bounds_issues(transform.get("external"), "transform.external")
        if "invert" in transform and not isinstance(transform["invert"], bool):
            issues.append(Issue("transform.invert", "transform.invert must be a boolean."))
        return issues
    if kind == TransformType.LINEAR:
        return _linear_issues(transform)
    return []


def tag_names_issues(tag_names, field: str = "tag_names") -> list[Issue]:
    if not isinstance(tag_names, list) or not tag_names:
        return [Issue(field, f"{field} must be a non-empty list.")]
    if not all(isinstance(name, str) and name.strip() for name in tag_names):
        return [Issue(field, f"{field} must hold non-empty strings.")]
    if any(len(name) > TAG_NAME_MAX_LENGTH for name in tag_names):
        return [Issue(field, f"{field} must be at most {TAG_NAME_MAX_LENGTH} characters long.")]
    if repeated := duplicates(tag_names):
        return [Issue(field, f"{field} repeats {repeated}.")]
    return []


def rule_issues(rule) -> list[Issue]:
    """Every problem of a rule; an empty list means the engine can run it."""
    if not isinstance(rule, dict):
        return [Issue("", "A rule must be an object.")]
    issues = tag_names_issues(rule.get("tag_names"))
    external = rule.get("external")
    value_type = external.get("value_type") if isinstance(external, dict) else None
    if value_type not in ValueType.values:
        issues.append(Issue("external.value_type", f"external.value_type must be one of {ValueType.values}."))
    direction = rule.get("direction", Direction.BOTH)
    if direction not in Direction.values:
        issues.append(Issue("direction", f"direction must be one of {Direction.values}."))
    on_invalid = rule.get("on_invalid", OnInvalid.REJECT)
    if on_invalid not in OnInvalid.values:
        issues.append(Issue("on_invalid", f"on_invalid must be one of {OnInvalid.values}."))
    if issues:  # the checks below rely on value_type and direction
        return issues
    if on_invalid == OnInvalid.CLAMP and value_type not in NUMERIC_VALUE_TYPES:
        issues.append(Issue("on_invalid", "on_invalid clamp needs a numeric value_type."))
    if on_invalid == OnInvalid.CONST and rule.get("on_invalid_value") is None:
        issues.append(Issue("on_invalid_value", "on_invalid const needs on_invalid_value."))
    elif on_invalid != OnInvalid.CONST and rule.get("on_invalid_value") is not None:
        issues.append(Issue("on_invalid_value", "on_invalid_value is used only with on_invalid const."))
    issues += _transform_issues(rule.get("transform"), value_type, direction)
    return issues


def rule_errors(rule) -> list[str]:
    """The messages of ``rule_issues``."""
    return [issue.message for issue in rule_issues(rule)]

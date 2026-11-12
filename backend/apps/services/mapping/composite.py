"""
Composite mapping: one integrator value made of several GRMS tags, and one integrator value
written back as an ordered list of tag writes.

A composite rule is a plain dict, held in ``MappingProfile.composite_rules``::

    {"id": "fcumode",
     "output": {"tag_name": "fcumode", "value_type": "integer"},
     "inputs": [{"alias": "power", "tag_name": "AC ON OFF", "source": "telemetry"},
                {"alias": "mode", "tag_name": "AC Mode", "source": "telemetry"}],
     "conditions": [{"when": {"power": 0}, "value": 0},
                    {"when": {"power": 1, "mode": "Heat"}, "value": 1},
                    {"when": {"power": 1, "mode": "Cool"}, "value": 2}],
     "actions": [{"value": 0, "set": [{"alias": "power", "value": 0}]},
                 {"value": 2, "set": [{"alias": "mode", "value": "Cool"}, {"alias": "power", "value": 1}]}],
     "on_no_match": "reject", "on_missing": "skip"}

Reads (``to_external``) take the GRMS values of the inputs by alias and return the value of the
condition they match; writes (``to_grms``) return the writes of the action of the integrator's
value. A condition constraint is a literal (equality, typed as in enum rules), ``{"in": [...]}``
or ``{"min": a, "max": b}`` (inclusive, either bound optional); an alias left out of ``when``
matches any value. Conditions must not overlap with different values, so the first match is the
only one. No database access: ``services.utils.composite_tags`` feeds the room's values in.
"""

import re
from typing import Any

from services.mapping.constants import (
    ALIAS_PATTERN,
    COMPOSITE_ID_PATTERN,
    TAG_NAME_MAX_LENGTH,
    Direction,
    OnMissing,
    OnNoMatch,
    Source,
    ValueType,
)
from services.mapping.engine import SKIP, MappingError, applies, coerce, is_number, value_key
from services.mapping.validation import Issue, duplicates, matches_value_type
from services.serializers.device_tag_types import range_allowed

# Why an input has no usable value; each is the MappingError code a read reports for it.
MISSING = "missing_input"
AMBIGUOUS = "ambiguous_source"

_CONSTRAINT_KEYS = {"in", "min", "max"}


def _number(value) -> float | None:
    """``value`` as a number for a ``min``/``max`` constraint; a device may store it as a string."""
    if is_number(value):
        return value
    if isinstance(value, str):
        try:
            return coerce(value, ValueType.NUMBER)
        except MappingError:
            return None
    return None


def _is_scalar(value) -> bool:
    return isinstance(value, str | bool) or is_number(value)


def satisfies(constraint, value) -> bool:
    """Whether a GRMS value meets one ``when`` constraint."""
    if isinstance(constraint, dict):
        if "in" in constraint:
            return value_key(value) in {value_key(item) for item in constraint["in"]}
        number = _number(value)
        if number is None:
            return False
        low, high = constraint.get("min"), constraint.get("max")
        return (low is None or number >= low) and (high is None or number <= high)
    return value_key(value) == value_key(constraint)


def _condition_matches(when: dict, values: dict, unavailable: dict) -> bool:
    return all(
        alias not in unavailable and values.get(alias) is not None and satisfies(constraint, values[alias])
        for alias, constraint in when.items()
    )


def inputs_by_alias(rule: dict) -> dict[str, dict]:
    return {item["alias"]: item for item in rule["inputs"]}


def to_external(rule: dict, values: dict, unavailable: dict | None = None):
    """GRMS input values (alias -> value) -> the integrator value, ``SKIP`` or ``MappingError``.

    ``unavailable`` maps an alias with no usable value to ``missing_input`` or ``ambiguous_source``. Such an input matters only when no condition matched without it: since
    conditions do not overlap, a match that ignores the input is the answer whatever its value."""
    if not applies(rule, Direction.TO_EXTERNAL):
        raise MappingError(f"The composite rule {rule['id']!r} does not convert reads.", "direction")
    unavailable = dict(unavailable or {})
    for item in rule["inputs"]:
        if values.get(item["alias"]) is None:
            unavailable.setdefault(item["alias"], MISSING)
    for condition in rule["conditions"]:
        if _condition_matches(condition["when"], values, unavailable):
            return condition["value"]
    relevant = [alias for alias in unavailable if any(alias in c["when"] for c in rule["conditions"])]
    if relevant:
        if rule.get("on_missing", OnMissing.SKIP) == OnMissing.SKIP:
            return SKIP
        alias = relevant[0]
        code = unavailable[alias]
        reason = {MISSING: "has no value", AMBIGUOUS: "is reported by several devices"}[code]
        raise MappingError(f"Input {alias!r} {reason}.", code, f"inputs.{alias}")
    on_no_match = rule.get("on_no_match", OnNoMatch.REJECT)
    if on_no_match == OnNoMatch.SKIP:
        return SKIP
    if on_no_match == OnNoMatch.CONST:
        return rule["default_value"]
    shown = {alias: values.get(alias) for alias in inputs_by_alias(rule)}
    raise MappingError(f"No condition matches the inputs {shown}.", "unmapped", "inputs")


def to_grms(rule: dict, value) -> Any:
    """An integrator value -> the writes of its action, in order: ``[{alias, tag_name, source,
    value, required}]``. Returns ``SKIP`` for a value with no action under ``on_no_match: skip``
    and raises ``MappingError`` otherwise (``const`` defines a read default only)."""
    if not applies(rule, Direction.TO_GRMS):
        raise MappingError(f"The composite rule {rule['id']!r} does not accept writes.", "direction")
    value = coerce(value, rule["output"]["value_type"])
    inputs = inputs_by_alias(rule)
    for action in rule["actions"]:
        if value_key(action["value"]) == value_key(value):
            return [
                {
                    "alias": item["alias"],
                    "tag_name": inputs[item["alias"]]["tag_name"],
                    "source": inputs[item["alias"]]["source"],
                    "value": item["value"],
                    "required": item.get("required", True),
                }
                for item in action["set"]
            ]
    if rule.get("on_no_match", OnNoMatch.REJECT) == OnNoMatch.SKIP:
        return SKIP
    raise MappingError(f"No action for the value {value!r}.", "unmapped")


def output_ranges(rule: dict) -> list:
    """The values the output takes: ``output.tag_ranges`` when set, else every condition, default
    and action value of the directions the rule converts."""
    if rule["output"].get("tag_ranges") is not None:
        return rule["output"]["tag_ranges"]
    values = []
    if applies(rule, Direction.TO_EXTERNAL):
        values += [condition["value"] for condition in rule["conditions"]]
        if rule.get("on_no_match") == OnNoMatch.CONST:
            values.append(rule["default_value"])
    if applies(rule, Direction.TO_GRMS):
        values += [action["value"] for action in rule["actions"]]
    seen, unique = set(), []
    for value in values:
        if value_key(value) not in seen:
            seen.add(value_key(value))
            unique.append(value)
    return unique


# ---- Validation ---------------------------------------------------------------------------------


def _constraint_issues(constraint, field: str) -> list[Issue]:
    if not isinstance(constraint, dict):
        return [] if _is_scalar(constraint) else [Issue(field, "A constraint must be a string, number or boolean.")]
    if not constraint or set(constraint) - _CONSTRAINT_KEYS or ("in" in constraint and len(constraint) > 1):
        return [Issue(field, 'A constraint object is {"in": [...]} or {"min": a, "max": b}.')]
    if "in" in constraint:
        items = constraint["in"]
        if not isinstance(items, list) or not items or not all(_is_scalar(item) for item in items):
            return [Issue(f"{field}.in", "in must be a non-empty list of strings, numbers or booleans.")]
        return []
    low, high = constraint.get("min"), constraint.get("max")
    if any(bound is not None and not is_number(bound) for bound in (low, high)):
        return [Issue(field, "min and max must be numbers.")]
    if low is not None and high is not None and low > high:
        return [Issue(f"{field}.min", "min must not exceed max.")]
    return []


def _overlap(first, second) -> bool:
    """Whether a value may meet both constraints; ``None`` is an alias left out (any value)."""
    if first is None or second is None:
        return True
    if isinstance(second, dict) and "in" not in second and not (isinstance(first, dict) and "in" not in first):
        first, second = second, first  # an interval, if any, goes first
    if isinstance(first, dict) and "in" not in first:
        if isinstance(second, dict) and "in" not in second:
            low = max(b for b in (first.get("min"), second.get("min"), float("-inf")) if b is not None)
            high = min(b for b in (first.get("max"), second.get("max"), float("inf")) if b is not None)
            return low <= high
        items = second["in"] if isinstance(second, dict) else [second]
        return any(satisfies(first, item) for item in items)
    first_items = first["in"] if isinstance(first, dict) else [first]
    second_items = second["in"] if isinstance(second, dict) else [second]
    return bool({value_key(item) for item in first_items} & {value_key(item) for item in second_items})


def _conditions_overlap(first: dict, second: dict) -> bool:
    return all(_overlap(first.get(alias), second.get(alias)) for alias in {*first, *second})


def _inputs_issues(inputs) -> list[Issue]:
    if not isinstance(inputs, list) or not inputs:
        return [Issue("inputs", "inputs must be a non-empty list.")]
    issues = []
    for index, item in enumerate(inputs):
        field = f"inputs[{index}]"
        if not isinstance(item, dict):
            issues.append(Issue(field, "An input must be an object."))
            continue
        if not isinstance(item.get("alias"), str) or not re.match(ALIAS_PATTERN, item["alias"]):
            issues.append(Issue(f"{field}.alias", "alias must be a letter or _ followed by letters, digits or _."))
        name = item.get("tag_name")
        if not isinstance(name, str) or not name.strip() or len(name) > TAG_NAME_MAX_LENGTH:
            issues.append(Issue(f"{field}.tag_name", f"tag_name must be a string of 1..{TAG_NAME_MAX_LENGTH}."))
        if item.get("source") not in Source.values:
            issues.append(Issue(f"{field}.source", f"source must be one of {Source.values}."))
    if issues:
        return issues
    if repeated := duplicates(item["alias"] for item in inputs):
        issues.append(Issue("inputs", f"Aliases {repeated} repeat."))
    if repeated := duplicates([item["source"], item["tag_name"]] for item in inputs):
        issues.append(Issue("inputs", f"Tags {repeated} are read by several inputs."))
    return issues


def _output_issues(output) -> list[Issue]:
    if not isinstance(output, dict):
        return [Issue("output", "output must be an object with tag_name and value_type.")]
    issues = []
    name = output.get("tag_name")
    if not isinstance(name, str) or not name.strip() or len(name) > TAG_NAME_MAX_LENGTH:
        issues.append(Issue("output.tag_name", f"tag_name must be a string of 1..{TAG_NAME_MAX_LENGTH}."))
    if output.get("value_type") not in ValueType.values:
        issues.append(Issue("output.value_type", f"value_type must be one of {ValueType.values}."))
    if output.get("tag_type") is not None and not isinstance(output["tag_type"], str):
        issues.append(Issue("output.tag_type", "tag_type must be a string."))
    if output.get("tag_ranges") is not None and not isinstance(output["tag_ranges"], list):
        issues.append(Issue("output.tag_ranges", "tag_ranges must be a list."))
    return issues


def _output_value_issues(value, output: dict, field: str) -> list[Issue]:
    value_type = output["value_type"]
    if not matches_value_type(value, value_type):
        return [Issue(field, f"{value!r} is not {value_type}.")]
    if output.get("tag_ranges") is not None and not range_allowed(value, output["tag_ranges"]):
        return [Issue(field, f"{value!r} is not allowed by output.tag_ranges.")]
    return []


def _conditions_issues(rule: dict, aliases: set) -> list[Issue]:
    conditions = rule.get("conditions")
    if not isinstance(conditions, list) or not conditions:
        return [Issue("conditions", "Reads need a non-empty list of conditions.")]
    issues = []
    for index, condition in enumerate(conditions):
        field = f"conditions[{index}]"
        if not isinstance(condition, dict) or not isinstance(condition.get("when"), dict) or "value" not in condition:
            issues.append(Issue(field, "A condition is an object with when (an object) and value."))
            continue
        for alias, constraint in condition["when"].items():
            if alias not in aliases:
                issues.append(Issue(f"{field}.when.{alias}", f"{alias!r} is not an input alias."))
            else:
                issues += _constraint_issues(constraint, f"{field}.when.{alias}")
        issues += _output_value_issues(condition["value"], rule["output"], f"{field}.value")
    if issues:
        return issues
    for second in range(len(conditions)):
        for first in range(second):
            one, other = conditions[first], conditions[second]
            if value_key(one["value"]) != value_key(other["value"]) and _conditions_overlap(one["when"], other["when"]):
                message = f"Overlaps conditions[{first}] with another value: an input set would match both."
                issues.append(Issue(f"conditions[{second}]", message, "conflict"))
    return issues


def _actions_issues(rule: dict, aliases: set) -> list[Issue]:
    actions = rule.get("actions")
    if not isinstance(actions, list) or not actions:
        return [Issue("actions", "Writes need a non-empty list of actions.")]
    issues = []
    for index, action in enumerate(actions):
        field = f"actions[{index}]"
        if not isinstance(action, dict) or "value" not in action:
            issues.append(Issue(field, "An action is an object with value and set."))
            continue
        issues += _output_value_issues(action["value"], rule["output"], f"{field}.value")
        writes = action.get("set")
        if not isinstance(writes, list) or not writes:
            issues.append(Issue(f"{field}.set", "set must be a non-empty list."))
            continue
        for position, item in enumerate(writes):
            item_field = f"{field}.set[{position}]"
            if not isinstance(item, dict) or item.get("alias") not in aliases:
                issues.append(Issue(f"{item_field}.alias", "alias must name an input."))
            elif not _is_scalar(item.get("value")):
                issues.append(Issue(f"{item_field}.value", "value must be a string, number or boolean."))
            elif "required" in item and not isinstance(item["required"], bool):
                issues.append(Issue(f"{item_field}.required", "required must be a boolean."))
        if not issues and (repeated := duplicates(item["alias"] for item in writes)):
            issues.append(Issue(f"{field}.set", f"Aliases {repeated} are written twice."))
    if not issues and (repeated := duplicates(action["value"] for action in actions)):
        issues.append(Issue("actions", f"Values {repeated} have several actions: a write would be ambiguous."))
    return issues


def _round_trip_issues(rule: dict) -> list[Issue]:
    """An action must not set inputs that read back as another value: writing 2 then reading
    the result must give 2. Checked against the conditions the written values fully decide."""
    issues = []
    for index, action in enumerate(rule["actions"]):
        written = {item["alias"]: item["value"] for item in action["set"]}
        for position, condition in enumerate(rule["conditions"]):
            decided = all(alias in written for alias in condition["when"])
            if (
                decided
                and _condition_matches(condition["when"], written, {})
                and value_key(condition["value"]) != value_key(action["value"])
            ):
                message = f"The writes read back as {condition['value']!r} by conditions[{position}]."
                issues.append(Issue(f"actions[{index}]", message, "conflict"))
                break
    return issues


def composite_rule_issues(rule) -> list[Issue]:
    """Every problem of a composite rule; an empty list means the engine can run it."""
    if not isinstance(rule, dict):
        return [Issue("", "A composite rule must be an object.")]
    issues = []
    if not isinstance(rule.get("id"), str) or not re.match(COMPOSITE_ID_PATTERN, rule["id"]):
        issues.append(Issue("id", "id must be 1..64 letters, digits, '_', '.' or '-'."))
    issues += _output_issues(rule.get("output"))
    issues += _inputs_issues(rule.get("inputs"))
    direction = rule.get("direction", Direction.BOTH)
    if direction not in Direction.values:
        issues.append(Issue("direction", f"direction must be one of {Direction.values}."))
    on_no_match = rule.get("on_no_match", OnNoMatch.REJECT)
    if on_no_match not in OnNoMatch.values:
        issues.append(Issue("on_no_match", f"on_no_match must be one of {OnNoMatch.values}."))
    if rule.get("on_missing", OnMissing.SKIP) not in OnMissing.values:
        issues.append(Issue("on_missing", f"on_missing must be one of {OnMissing.values}."))
    if issues:  # the checks below rely on the output, the inputs and the direction
        return issues

    output = rule["output"]
    if output["tag_name"] in {item["tag_name"] for item in rule["inputs"]}:
        issues.append(Issue("output.tag_name", "The output cannot be one of the inputs."))
    if on_no_match == OnNoMatch.CONST:
        if direction == Direction.TO_GRMS:
            issues.append(Issue("on_no_match", "on_no_match const sets a read default: the rule has no reads."))
        elif rule.get("default_value") is None:
            issues.append(Issue("default_value", "on_no_match const needs default_value."))
        else:
            issues += _output_value_issues(rule["default_value"], output, "default_value")
    elif rule.get("default_value") is not None:
        issues.append(Issue("default_value", "default_value is used only with on_no_match const."))

    aliases = {item["alias"] for item in rule["inputs"]}
    reads, writes = direction != Direction.TO_GRMS, direction != Direction.TO_EXTERNAL
    read_issues = _conditions_issues(rule, aliases) if reads else []
    write_issues = _actions_issues(rule, aliases) if writes else []
    issues += read_issues + write_issues
    if reads and writes and not read_issues and not write_issues:
        issues += _round_trip_issues(rule)
    return issues


def round_trip_warnings(rule: dict) -> list[Issue]:
    """Actions whose writes decide no condition: the value they set cannot be checked to read back
    as itself. Not an error, but worth showing next to the action."""
    if not applies(rule, Direction.TO_EXTERNAL) or not applies(rule, Direction.TO_GRMS):
        return []
    warnings = []
    for index, action in enumerate(rule["actions"]):
        written = {item["alias"]: item["value"] for item in action["set"]}
        if not any(
            all(alias in written for alias in condition["when"]) and _condition_matches(condition["when"], written, {})
            for condition in rule["conditions"]
        ):
            message = "The writes decide no condition: a read may not give this value back."
            warnings.append(Issue(f"actions[{index}]", message, "round_trip"))
    return warnings


def composite_rules_issues(rules, plain_tag_names=()) -> tuple[list[list[Issue]], list[Issue]]:
    """Issues of a profile's ``composite_rules``: a list per rule by index, and the issues of the
    list as a whole (repeated ids or outputs, an output that a plain rule converts too)."""
    if not isinstance(rules, list):
        return [], [Issue("", "composite_rules must be a list.")]
    per_rule = [composite_rule_issues(rule) for rule in rules]
    if any(per_rule):
        return per_rule, []
    general = []
    if repeated := duplicates(rule["id"] for rule in rules):
        general.append(Issue("", f"Composite rule ids {repeated} repeat."))
    if repeated := duplicates(rule["output"]["tag_name"] for rule in rules):
        general.append(Issue("", f"Output tags {repeated} are produced by several composite rules."))
    if taken := sorted({rule["output"]["tag_name"] for rule in rules} & set(plain_tag_names)):
        general.append(Issue("", f"Output tags {taken} already have a rule in rules."))
    return per_rule, general

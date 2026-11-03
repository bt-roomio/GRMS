"""
Dry runs of mapping rules for the rule editor: a rule (saved or not) converts a value one way
and reports what it would do. Nothing is stored and nothing is sent to a device.

A run returns ``{"success", "skipped", "result", "actions", "errors", "warnings"}``. An error or
warning is ``{"field", "code", "message"}``; ``field`` is the path in the request (``rule.transform.map``,
``composite_rule.conditions[1].when.mode``, ``value``, ``inputs.mode``) for the form to show it at.
"""

from services.mapping import composite, engine
from services.mapping.constants import Direction, OnInvalid
from services.mapping.engine import SKIP, MappingError, applies
from services.mapping.validation import Issue, rule_issues

PLAIN = "rule"
COMPOSITE = "composite_rule"


def _report(**fields) -> dict:
    report = {"success": True, "skipped": False, "result": None, "actions": None, "errors": [], "warnings": []}
    report.update(fields)
    return report


def _prefixed(issues: list[Issue], prefix: str) -> list[dict]:
    return [{**issue.as_dict(), "field": f"{prefix}.{issue.field}" if issue.field else prefix} for issue in issues]


def _failed(error: MappingError, **fields) -> dict:
    return _report(success=False, errors=[error.as_dict()], **fields)


def run_rule(rule: dict, direction: str, value, tag_ranges=None, prefix: str = PLAIN) -> dict:
    """A plain rule converting ``value``; ``tag_ranges`` are the GRMS ranges of the tag (checked on
    ``to_grms``, converted on ``to_external``)."""
    if issues := rule_issues(rule):
        return _report(success=False, errors=_prefixed(issues, prefix))
    if not applies(rule, direction):
        reason = "reads" if direction == Direction.TO_EXTERNAL else "writes"
        return _failed(MappingError(f"The rule does not convert {reason}.", "direction", "direction"))
    try:
        if direction == Direction.TO_EXTERNAL:
            report = _report(result=engine.to_external(rule, value))
            if tag_ranges is not None:
                report["tag_ranges"] = engine.ranges_to_external(rule, tag_ranges)
            return report
        result = engine.to_grms(rule, value, tag_ranges)
    except MappingError as exc:
        return _failed(exc)
    if result is SKIP:
        return _report(skipped=True)
    report = _report(result=result)
    if rule.get("on_invalid") == OnInvalid.CONST and engine.value_key(result) == engine.value_key(
        rule["on_invalid_value"]
    ):
        message = "The value may have been replaced by on_invalid_value."
        report["warnings"].append({"field": "value", "code": "const", "message": message})
    return report


def run_composite(
    rule: dict, direction: str, value=None, inputs=None, unavailable=None, prefix: str = COMPOSITE, plan=None
) -> dict:
    """A composite rule: ``to_external`` reads ``inputs`` (alias -> GRMS value, ``unavailable``
    alias -> why it has none), ``to_grms`` lists the writes of ``value``. ``plan`` replaces
    ``composite.to_grms`` to resolve the writes against a room."""
    if issues := composite.composite_rule_issues(rule):
        return _report(success=False, errors=_prefixed(issues, prefix))
    warnings = _prefixed(composite.round_trip_warnings(rule), prefix)
    try:
        if direction == Direction.TO_EXTERNAL:
            inputs = inputs or {}
            aliases = composite.inputs_by_alias(rule)
            for alias in inputs:
                if alias not in aliases:
                    warnings.append({"field": f"inputs.{alias}", "code": "unknown_alias", "message": "Not an input."})
            result = composite.to_external(rule, inputs, unavailable)
            if result is SKIP:
                # The same run under reject says why the value was skipped.
                strict = {**rule, "on_missing": "reject", "on_no_match": "reject"}
                try:
                    composite.to_external(strict, inputs, unavailable)
                except MappingError as exc:
                    warnings.append({**exc.as_dict(), "message": f"Skipped: {exc}"})
                return _report(skipped=True, warnings=warnings)
            return _report(result=result, warnings=warnings)
        writes = (plan or composite.to_grms)(rule, value)
    except MappingError as exc:
        return _failed(exc, warnings=warnings)
    if writes is SKIP:
        return _report(skipped=True, actions=[], warnings=warnings)
    return _report(actions=writes, warnings=warnings)

"""
``KeyFilterPredicate`` evaluation — NUMERIC, BOOLEAN, STRING and the recursive
COMPLEX, ported from TB's predicate semantics.

A missing value never satisfies a predicate: a device that has never reported a
key must not trip a ``NOT_EQUAL`` rule.
"""

from typing import Any

from alarms.constants import (
    MAX_COMPLEX_DEPTH,
    PREDICATE_BOOLEAN,
    PREDICATE_COMPLEX,
    PREDICATE_NUMERIC,
    PREDICATE_STRING,
    VALUE_BOOLEAN,
    VALUE_NUMERIC,
    VALUE_STRING,
)
from alarms.services.dynamic import resolve_value
from alarms.services.snapshot import DataSnapshot, to_bool, to_float

NUMERIC_OPS = {
    "EQUAL": lambda actual, expected: actual == expected,
    "NOT_EQUAL": lambda actual, expected: actual != expected,
    "GREATER": lambda actual, expected: actual > expected,
    "LESS": lambda actual, expected: actual < expected,
    "GREATER_OR_EQUAL": lambda actual, expected: actual >= expected,
    "LESS_OR_EQUAL": lambda actual, expected: actual <= expected,
}

STRING_OPS = {
    "EQUAL": lambda actual, expected: actual == expected,
    "NOT_EQUAL": lambda actual, expected: actual != expected,
    "STARTS_WITH": lambda actual, expected: actual.startswith(expected),
    "ENDS_WITH": lambda actual, expected: actual.endswith(expected),
    "CONTAINS": lambda actual, expected: expected in actual,
    "NOT_CONTAINS": lambda actual, expected: expected not in actual,
    "IN": lambda actual, expected: actual in split_list(expected),
    "NOT_IN": lambda actual, expected: actual not in split_list(expected),
}


def split_list(expected: Any) -> list[str]:
    if isinstance(expected, (list, tuple, set)):
        return [str(item) for item in expected]
    return [item.strip() for item in str(expected).split(",") if item.strip()]


def eval_predicate(predicate: dict, actual: Any, snapshot: DataSnapshot, value_type: str, depth: int = 1) -> bool:
    predicate_type = predicate.get("type")

    if predicate_type == PREDICATE_COMPLEX:
        if depth > MAX_COMPLEX_DEPTH:
            return False
        results = (
            eval_predicate(child, actual, snapshot, value_type, depth + 1)
            for child in predicate.get("predicates") or []
        )
        return all(results) if predicate.get("operation") == "AND" else any(results)

    if actual is None:
        return False

    expected = resolve_value(predicate.get("value"), snapshot, expected_value_type(predicate_type, value_type))
    if expected is None:
        return False

    if predicate_type == PREDICATE_NUMERIC:
        actual_number, expected_number = to_float(actual), to_float(expected)
        if actual_number is None or expected_number is None:
            return False
        return NUMERIC_OPS[predicate["operation"]](actual_number, expected_number)

    if predicate_type == PREDICATE_BOOLEAN:
        actual_flag, expected_flag = to_bool(actual), to_bool(expected)
        if actual_flag is None or expected_flag is None:
            return False
        return (actual_flag == expected_flag) if predicate["operation"] == "EQUAL" else (actual_flag != expected_flag)

    if predicate_type == PREDICATE_STRING:
        operation = predicate["operation"]
        actual_text = str(actual)
        # Only IN/NOT_IN take a list; every other operation wants one string.
        expected_text = expected if operation in ("IN", "NOT_IN") and isinstance(expected, list) else str(expected)

        if predicate.get("ignoreCase"):
            actual_text = actual_text.lower()
            expected_text = (
                [str(item).lower() for item in expected_text]
                if isinstance(expected_text, list)
                else expected_text.lower()
            )

        return STRING_OPS[operation](actual_text, expected_text)

    return False


def expected_value_type(predicate_type: str | None, value_type: str) -> str:
    """
    A DATE_TIME filter reads its key as an epoch but its threshold as a number,
    so the predicate's own type decides how the threshold is coerced.
    """
    if predicate_type == PREDICATE_NUMERIC:
        return VALUE_NUMERIC
    if predicate_type == PREDICATE_BOOLEAN:
        return VALUE_BOOLEAN
    if predicate_type == PREDICATE_STRING:
        return VALUE_STRING
    return value_type


def eval_filter(condition_filter: dict, snapshot: DataSnapshot) -> bool:
    key = condition_filter["key"]
    value_type = condition_filter["valueType"]
    actual = snapshot.typed(key["type"], key.get("key") or "", value_type, condition_filter.get("value"))
    return eval_predicate(condition_filter["predicate"], actual, snapshot, value_type)


def eval_condition(filters: list[dict], snapshot: DataSnapshot) -> bool:
    """Filters are ANDed, as in TB; OR belongs inside a COMPLEX predicate."""
    return bool(filters) and all(eval_filter(condition_filter, snapshot) for condition_filter in filters)

"""
``AlarmConditionSpec`` — how long, or how often, the condition has to hold.

The counters live in ``AlarmRuleState.state`` because the evaluator is a
periodic task and has no memory of its own between ticks.
"""

from datetime import datetime, timedelta

from django.utils.dateparse import parse_datetime

from alarms.constants import (
    SPEC_DURATION,
    SPEC_REPEATING,
    TIME_UNIT_SECONDS,
    VALUE_NUMERIC,
)
from alarms.services.dynamic import resolve_value
from alarms.services.snapshot import DataSnapshot

DEFAULT_REPEAT_COUNT = 1


def eval_spec(
    spec: dict | None,
    state: dict | None,
    matched: bool,
    now: datetime,
    snapshot: DataSnapshot,
) -> tuple[bool, dict | None]:
    """
    Returns ``(fired, new_state)``.

    ``new_state`` of ``None`` means "forget this rule" — a broken streak resets
    both the duration clock and the repeat counter, because both specs require
    the condition to hold *continuously*.
    """
    spec = spec or {}
    spec_type = spec.get("type")

    if not matched:
        return False, None

    if spec_type == SPEC_DURATION:
        seconds = duration_seconds(spec, snapshot)
        since = parse_datetime((state or {}).get("since") or "") or now
        fired = seconds is not None and (now - since) >= timedelta(seconds=seconds)
        return fired, {"since": since.isoformat()}

    if spec_type == SPEC_REPEATING:
        target = repeat_count(spec, snapshot)
        count = int((state or {}).get("count") or 0) + 1
        return count >= target, {"count": count}

    return True, None


def duration_seconds(spec: dict, snapshot: DataSnapshot) -> float | None:
    value = resolve_value(spec.get("predicate"), snapshot, VALUE_NUMERIC)
    if value is None or value <= 0:
        return None
    unit = TIME_UNIT_SECONDS.get(spec.get("unit") or "SECONDS", 1)
    return float(value) * unit


def repeat_count(spec: dict, snapshot: DataSnapshot) -> int:
    value = resolve_value(spec.get("predicate"), snapshot, VALUE_NUMERIC)
    if value is None or value < 1:
        return DEFAULT_REPEAT_COUNT
    return int(value)

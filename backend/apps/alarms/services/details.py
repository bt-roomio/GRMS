"""
``alarmDetails`` rendering.

``string.Template`` cannot be used: TB placeholders are real telemetry keys and
those contain spaces (``${Room Temperature}``). An unknown placeholder is left
standing rather than raising — a typo in a rule must not kill the whole tick.
"""

import re
from typing import Any

from alarms.constants import KEY_CONSTANT
from alarms.services.snapshot import DataSnapshot

PLACEHOLDER = re.compile(r"\$\{([^}]+)\}")


def service_values(snapshot: DataSnapshot, alarm_type: str, severity: str) -> dict[str, Any]:
    return {
        "originatorName": snapshot.device_name,
        "room": snapshot.room_number or "",
        "alarmType": alarm_type,
        "alarmSeverity": severity,
    }


def render(template: str | None, snapshot: DataSnapshot, alarm_type: str, severity: str) -> str:
    if not template:
        return f"{alarm_type} — {snapshot.device_name}"

    extras = service_values(snapshot, alarm_type, severity)

    def substitute(match: re.Match) -> str:
        name = match.group(1).strip()
        value = extras[name] if name in extras else snapshot.raw(name)
        return match.group(0) if value is None else str(value)

    return PLACEHOLDER.sub(substitute, template)


def matched_values(filters: list[dict], snapshot: DataSnapshot) -> dict[str, Any]:
    """The values that tripped the rule, kept on the alarm for the UI card."""
    values = {}
    for condition_filter in filters:
        key = condition_filter.get("key") or {}
        if key.get("type") == KEY_CONSTANT:
            continue
        name = key.get("key")
        if not name:
            continue
        values[name] = snapshot.raw(name)
    return values

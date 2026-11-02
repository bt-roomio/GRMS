"""
What a notification says, independent of how a channel lays it out.

Telegram and email render the same lines — one per alarm, capped at
``MAX_LINES`` — so the two never disagree about what happened.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from alarms.constants import AlarmSeverity
from alarms.models import Alarm

MAX_LINES = 20

SEVERITY_ICONS = {
    AlarmSeverity.CRITICAL: "🔴",
    AlarmSeverity.MAJOR: "🟠",
    AlarmSeverity.MINOR: "🟡",
    AlarmSeverity.WARNING: "🔵",
    AlarmSeverity.INDETERMINATE: "⚪",
}

RAISED_TITLE = "Новые аварии"
CLEARED_TITLE = "Снятые аварии"


@dataclass(frozen=True)
class AlarmLine:
    icon: str
    severity: str
    time: str
    room: str | None
    text: str


def tenant_title(tenant) -> str:
    return tenant.title or "GRMS"


def alarm_lines(alarms: list[Alarm], offset: int, raised: bool) -> list[AlarmLine]:
    lines = []
    for alarm in alarms[:MAX_LINES]:
        moment = alarm.start_ts if raised else (alarm.clear_ts or alarm.end_ts)
        lines.append(
            AlarmLine(
                icon=SEVERITY_ICONS.get(alarm.severity, "⚪"),
                severity=alarm.severity,
                time=format_time(moment, offset),
                room=str(alarm.room.number) if alarm.room_id else None,
                text=str((alarm.details or {}).get("message") or alarm.alarm_type),
            )
        )
    return lines


def overflow(alarms: list[Alarm]) -> str | None:
    if len(alarms) > MAX_LINES:
        return f"… и ещё {len(alarms) - MAX_LINES}"
    return None


def timezone_offset(tenant) -> int:
    """``general_settings.timezone`` is a whole-hour offset in this project."""
    info = tenant.additional_info if isinstance(tenant.additional_info, dict) else {}
    try:
        return int((info.get("general_settings") or {}).get("timezone") or 0)
    except (TypeError, ValueError):
        return 0


def format_time(moment: datetime | None, offset: int) -> str:
    if moment is None:
        return "—"
    return (moment + timedelta(hours=offset)).strftime("%d.%m %H:%M")

"""``AlarmSchedule`` — when a rule is allowed to fire at all."""

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from alarms.constants import SCHEDULE_CUSTOM, SCHEDULE_SPECIFIC_TIME

MS_PER_DAY = 24 * 60 * 60 * 1000


def zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def ms_from_midnight(moment: datetime) -> int:
    return ((moment.hour * 60 + moment.minute) * 60 + moment.second) * 1000 + moment.microsecond // 1000


def in_window(offset: int, starts_on: int, ends_on: int) -> bool:
    if starts_on == ends_on:
        # A zero-length window in TB means the whole day.
        return True
    if starts_on < ends_on:
        return starts_on <= offset < ends_on
    # Wraps past midnight, e.g. 22:00 → 06:00.
    return offset >= starts_on or offset < ends_on


def is_active_at(schedule: dict | None, moment: datetime) -> bool:
    if not schedule:
        return True

    schedule_type = schedule.get("type")

    if schedule_type == SCHEDULE_SPECIFIC_TIME:
        local = moment.astimezone(zone(schedule.get("timezone")))
        if local.isoweekday() not in set(schedule.get("daysOfWeek") or []):
            return False
        return in_window(ms_from_midnight(local), schedule.get("startsOn") or 0, schedule.get("endsOn") or 0)

    if schedule_type == SCHEDULE_CUSTOM:
        local = moment.astimezone(zone(schedule.get("timezone")))
        for item in schedule.get("items") or []:
            if item.get("dayOfWeek") != local.isoweekday():
                continue
            if not item.get("enabled"):
                return False
            return in_window(ms_from_midnight(local), item.get("startsOn") or 0, item.get("endsOn") or 0)
        return False

    return True

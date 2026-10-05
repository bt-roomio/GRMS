from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from alarms.services.schedule import is_active_at

UTC = ZoneInfo("UTC")


def at(year, month, day, hour, minute=0, tz=UTC):
    return datetime(year, month, day, hour, minute, tzinfo=tz)


def hours(value: float) -> int:
    return int(value * 60 * 60 * 1000)


class AnyTimeScheduleTest(SimpleTestCase):
    def test_no_schedule_is_always_active(self):
        self.assertTrue(is_active_at(None, at(2026, 9, 3, 12)))
        self.assertTrue(is_active_at({"type": "ANY_TIME"}, at(2026, 9, 3, 3)))


class SpecificTimeScheduleTest(SimpleTestCase):
    def schedule(self, days, starts, ends, timezone_name="UTC"):
        return {
            "type": "SPECIFIC_TIME",
            "timezone": timezone_name,
            "daysOfWeek": days,
            "startsOn": hours(starts),
            "endsOn": hours(ends),
        }

    def test_inside_and_outside_the_window(self):
        # 2026-09-03 is a Thursday (ISO weekday 4).
        schedule = self.schedule([4], 9, 18)
        self.assertTrue(is_active_at(schedule, at(2026, 9, 3, 12)))
        self.assertFalse(is_active_at(schedule, at(2026, 9, 3, 8)))
        self.assertFalse(is_active_at(schedule, at(2026, 9, 3, 18)))

    def test_wrong_day_of_week(self):
        self.assertFalse(is_active_at(self.schedule([1], 0, 24), at(2026, 9, 3, 12)))

    def test_window_wrapping_past_midnight(self):
        schedule = self.schedule([4], 22, 6)
        self.assertTrue(is_active_at(schedule, at(2026, 9, 3, 23)))
        self.assertTrue(is_active_at(schedule, at(2026, 9, 3, 2)))
        self.assertFalse(is_active_at(schedule, at(2026, 9, 3, 12)))

    def test_timezone_is_honoured(self):
        # 06:00 UTC is 11:00 in Tashkent, inside the window; the same instant
        # is outside it when the schedule is read as UTC.
        schedule = self.schedule([4], 9, 18, timezone_name="Asia/Tashkent")
        self.assertTrue(is_active_at(schedule, at(2026, 9, 3, 6)))
        self.assertFalse(is_active_at(self.schedule([4], 9, 18), at(2026, 9, 3, 6)))

    def test_unknown_timezone_falls_back_to_utc(self):
        schedule = self.schedule([4], 9, 18, timezone_name="Mars/Olympus")
        self.assertTrue(is_active_at(schedule, at(2026, 9, 3, 12)))


class CustomScheduleTest(SimpleTestCase):
    def schedule(self, items):
        return {"type": "CUSTOM", "timezone": "UTC", "items": items}

    def test_enabled_day_within_its_window(self):
        schedule = self.schedule([{"enabled": True, "dayOfWeek": 4, "startsOn": hours(9), "endsOn": hours(18)}])
        self.assertTrue(is_active_at(schedule, at(2026, 9, 3, 12)))
        self.assertFalse(is_active_at(schedule, at(2026, 9, 3, 20)))

    def test_disabled_day(self):
        schedule = self.schedule([{"enabled": False, "dayOfWeek": 4, "startsOn": 0, "endsOn": hours(24)}])
        self.assertFalse(is_active_at(schedule, at(2026, 9, 3, 12)))

    def test_a_day_with_no_item_is_inactive(self):
        schedule = self.schedule([{"enabled": True, "dayOfWeek": 1, "startsOn": 0, "endsOn": hours(24)}])
        self.assertFalse(is_active_at(schedule, at(2026, 9, 3, 12)))

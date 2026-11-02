from datetime import timedelta

from django.utils import timezone

from alarms.models import Alarm, AlarmComment, AlarmRuleState
from alarms.services.engine import evaluate
from alarms.tests.base import DEVICE_ID, ROOM_ID, AlarmTestCase, offline_rule, temperature_rule
from main.models import Room


class AlarmLifecycleTest(AlarmTestCase):
    def setUp(self):
        self.now = timezone.now()
        self.set_rules(offline_rule(minutes=0))
        self.set_attribute("active", False)

    def test_alarm_is_created_with_rendered_details(self):
        evaluate(now=self.now)

        alarm = Alarm.objects.get(originator_id=DEVICE_ID, alarm_type="Device Offline")
        self.assertEqual(alarm.severity, "MAJOR")
        self.assertFalse(alarm.cleared)
        self.assertEqual(alarm.status, "ACTIVE_UNACK")
        self.assertEqual(alarm.details["message"], "Устройство DHT11 Demo Device не на связи")
        self.assertEqual(alarm.details["values"], {"active": False})
        self.assertEqual(str(alarm.room_id), ROOM_ID)

    def test_a_second_tick_only_moves_end_ts(self):
        evaluate(now=self.now)
        later = self.now + timedelta(minutes=5)
        evaluate(now=later)

        alarm = Alarm.objects.get(originator_id=DEVICE_ID, alarm_type="Device Offline")
        self.assertEqual(Alarm.objects.count(), 1)
        self.assertEqual(alarm.start_ts, self.now)
        self.assertEqual(alarm.end_ts, later)

    def test_clear_rule_closes_the_alarm_and_leaves_an_audit_trail(self):
        evaluate(now=self.now)

        self.set_attribute("active", True)
        cleared_at = self.now + timedelta(minutes=20)
        evaluate(now=cleared_at)

        alarm = Alarm.objects.get(originator_id=DEVICE_ID, alarm_type="Device Offline")
        self.assertTrue(alarm.cleared)
        self.assertEqual(alarm.clear_ts, cleared_at)
        self.assertEqual(alarm.duration_ms, 20 * 60 * 1000)
        self.assertTrue(
            AlarmComment.objects.filter(
                alarm=alarm, alarm_comment_type=AlarmComment.TYPE.SYSTEM, comment__subtype="CLEARED"
            ).exists()
        )

    def test_without_a_clear_rule_the_alarm_stays_open(self):
        self.set_rules(offline_rule(minutes=0, clear=False))
        evaluate(now=self.now)

        self.set_attribute("active", True)
        evaluate(now=self.now + timedelta(minutes=20))

        self.assertFalse(Alarm.objects.get(originator_id=DEVICE_ID).cleared)

    def test_a_new_alarm_opens_after_the_previous_one_cleared(self):
        evaluate(now=self.now)
        self.set_attribute("active", True)
        evaluate(now=self.now + timedelta(minutes=10))

        self.set_attribute("active", False)
        evaluate(now=self.now + timedelta(minutes=20))

        self.assertEqual(Alarm.objects.filter(originator_id=DEVICE_ID).count(), 2)
        self.assertEqual(Alarm.objects.filter(originator_id=DEVICE_ID, cleared=False).count(), 1)


class SeverityEscalationTest(AlarmTestCase):
    def setUp(self):
        self.now = timezone.now()
        self.set_telemetry("Room Temperature", 31.0)

    def rule_with_two_severities(self):
        rule = temperature_rule(threshold=30, severity="MINOR", attribute=None)
        critical = temperature_rule(threshold=40, severity="CRITICAL", attribute=None)
        rule["createRules"]["CRITICAL"] = critical["createRules"]["CRITICAL"]
        return rule

    def test_the_most_severe_matching_rule_wins(self):
        self.set_rules(self.rule_with_two_severities())
        self.set_telemetry("Room Temperature", 45.0)
        evaluate(now=self.now)

        self.assertEqual(Alarm.objects.get(originator_id=DEVICE_ID).severity, "CRITICAL")

    def test_escalation_updates_severity_and_records_a_system_comment(self):
        self.set_rules(self.rule_with_two_severities())
        evaluate(now=self.now)
        self.assertEqual(Alarm.objects.get(originator_id=DEVICE_ID).severity, "MINOR")

        self.set_telemetry("Room Temperature", 45.0)
        evaluate(now=self.now + timedelta(minutes=1))

        alarm = Alarm.objects.get(originator_id=DEVICE_ID)
        self.assertEqual(alarm.severity, "CRITICAL")
        comment = AlarmComment.objects.get(alarm=alarm, comment__subtype="SEVERITY_CHANGED")
        self.assertEqual(comment.comment["from"], "MINOR")
        self.assertEqual(comment.comment["to"], "CRITICAL")
        self.assertEqual(Alarm.objects.count(), 1)


class DurationStateTest(AlarmTestCase):
    def setUp(self):
        self.now = timezone.now()
        self.set_rules(offline_rule(minutes=10))
        self.set_attribute("active", False)

    def test_nothing_fires_before_the_interval_elapses(self):
        evaluate(now=self.now)
        self.assertFalse(Alarm.objects.exists())
        # The clock has to survive between ticks, which is what the state row is for.
        self.assertTrue(AlarmRuleState.objects.filter(device_id=DEVICE_ID).exists())

        evaluate(now=self.now + timedelta(minutes=9))
        self.assertFalse(Alarm.objects.exists())

        evaluate(now=self.now + timedelta(minutes=10))
        self.assertTrue(Alarm.objects.filter(originator_id=DEVICE_ID).exists())

    def test_the_state_row_is_dropped_once_the_condition_stops_holding(self):
        evaluate(now=self.now)
        self.set_attribute("active", True)
        evaluate(now=self.now + timedelta(minutes=1))

        self.assertFalse(AlarmRuleState.objects.filter(device_id=DEVICE_ID).exists())


class DynamicThresholdTest(AlarmTestCase):
    def test_a_room_override_changes_the_threshold_for_that_room_only(self):
        now = timezone.now()
        self.set_rules(temperature_rule(threshold=30))
        self.set_telemetry("Room Temperature", 25.0)

        evaluate(now=now)
        self.assertFalse(Alarm.objects.exists())

        Room.objects.filter(pk=ROOM_ID).update(additional_info={"attributes": {"temperatureMax": 20}})
        evaluate(now=now + timedelta(minutes=1))

        alarm = Alarm.objects.get(originator_id=DEVICE_ID)
        self.assertEqual(alarm.alarm_type, "High Temperature")
        self.assertEqual(alarm.details["message"], "Температура 25.0° в номере 101")


class ScheduleTest(AlarmTestCase):
    def test_a_rule_outside_its_schedule_never_fires(self):
        rule = offline_rule(minutes=0)
        rule["createRules"]["MAJOR"]["schedule"] = {
            "type": "SPECIFIC_TIME",
            "timezone": "UTC",
            # A day that is never today.
            "daysOfWeek": [(timezone.now().isoweekday() % 7) + 1],
            "startsOn": 0,
            "endsOn": 24 * 60 * 60 * 1000,
        }
        self.set_rules(rule)
        self.set_attribute("active", False)

        evaluate(now=timezone.now())
        self.assertFalse(Alarm.objects.exists())


class MalformedRuleTest(AlarmTestCase):
    def test_a_broken_rule_does_not_stop_the_pass(self):
        broken = {"alarmType": "Broken", "createRules": {"MAJOR": {"condition": "not-an-object"}}}
        self.set_rules(broken, offline_rule(minutes=0))
        self.set_attribute("active", False)

        evaluate(now=timezone.now())

        self.assertTrue(Alarm.objects.filter(alarm_type="Device Offline").exists())
        self.assertFalse(Alarm.objects.filter(alarm_type="Broken").exists())

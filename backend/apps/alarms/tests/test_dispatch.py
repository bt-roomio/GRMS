from datetime import timedelta
from unittest.mock import patch

from django.core.cache import caches
from django.utils import timezone

from alarms.models import Alarm
from alarms.notifications.dispatcher import dispatch
from alarms.notifications.settings import SETTINGS_KEY
from alarms.telegram.exceptions import TelegramAPIError
from alarms.tests.base import DEVICE_ID, TENANT_ID, AlarmTestCase
from main.models import Tenant


class FakeChannel:
    """Stands in for TelegramChannel so no test touches the network."""

    name = "telegram"

    def __init__(self, error=None):
        self.sent = []
        self.error = error

    def is_configured(self, tenant_settings):
        return bool(tenant_settings.get("telegram_enabled") and tenant_settings.get("telegram_chat_id"))

    def send(self, tenant_settings, text):
        if self.error:
            raise self.error
        self.sent.append((tenant_settings["telegram_chat_id"], text))


class DispatcherTestCase(AlarmTestCase):
    def setUp(self):
        self.now = timezone.now()
        # The per-tenant rate limiter lives in Redis and outlives a test case,
        # so a run of these would otherwise throttle itself.
        caches["default"].delete(f"alarms:rate:{TENANT_ID}")
        self.configure()

    def configure(self, **overrides):
        tenant = Tenant.objects.get(pk=TENANT_ID)
        info = tenant.additional_info or {}
        info[SETTINGS_KEY] = {
            "telegram_enabled": True,
            "telegram_chat_id": "-100500",
            "notify_delay_sec": 300,
            "min_severity": "MINOR",
            **overrides,
        }
        Tenant.objects.filter(pk=TENANT_ID).update(additional_info=info)

    def make_alarm(self, minutes_ago=10, severity="MAJOR", alarm_type="Device Offline", **extra):
        start = self.now - timedelta(minutes=minutes_ago)
        return Alarm.objects.create(
            tenant_id=TENANT_ID,
            originator_id=DEVICE_ID,
            alarm_type=alarm_type,
            severity=severity,
            start_ts=start,
            end_ts=start,
            details={"message": f"{alarm_type} on DHT11"},
            **extra,
        )

    def run_dispatch(self, channel=None):
        channel = channel or FakeChannel()
        with patch("alarms.notifications.dispatcher.TelegramChannel", return_value=channel):
            stats = dispatch(now=self.now)
        return channel, stats


class DispatchTest(DispatcherTestCase):
    def test_an_alarm_older_than_the_delay_is_sent_once(self):
        alarm = self.make_alarm()

        channel, stats = self.run_dispatch()

        self.assertEqual(stats["raised"], 1)
        self.assertEqual(len(channel.sent), 1)
        chat_id, text = channel.sent[0]
        self.assertEqual(chat_id, "-100500")
        self.assertIn("Device Offline on DHT11", text)

        alarm.refresh_from_db()
        self.assertIsNotNone(alarm.notified_at)

    def test_running_twice_sends_nothing_the_second_time(self):
        self.make_alarm()
        self.run_dispatch()

        channel, stats = self.run_dispatch()
        self.assertEqual(stats["raised"], 0)
        self.assertEqual(channel.sent, [])

    def test_an_alarm_inside_the_delay_window_waits(self):
        self.make_alarm(minutes_ago=1)

        channel, stats = self.run_dispatch()
        self.assertEqual(stats["raised"], 0)
        self.assertEqual(channel.sent, [])

    def test_flapping_below_the_delay_is_never_announced(self):
        # Raised and cleared inside the window: it stays in the journal but
        # produces neither a raise nor a clear message.
        alarm = self.make_alarm(minutes_ago=1)
        alarm.cleared = True
        alarm.clear_ts = self.now
        alarm.save()

        channel, stats = self.run_dispatch()
        self.assertEqual(channel.sent, [])
        self.assertEqual(stats["cleared"], 0)

    def test_a_clear_is_announced_only_after_its_raise_was(self):
        alarm = self.make_alarm()
        self.run_dispatch()

        alarm.refresh_from_db()
        alarm.cleared = True
        alarm.clear_ts = self.now
        alarm.save()

        channel, stats = self.run_dispatch()
        self.assertEqual(stats["cleared"], 1)
        self.assertIn("Снятые аварии", channel.sent[0][1])

        alarm.refresh_from_db()
        self.assertIsNotNone(alarm.notified_clear_at)

    def test_min_severity_filters_out_the_quiet_ones(self):
        self.configure(min_severity="MAJOR")
        self.make_alarm(severity="WARNING", alarm_type="Low Temperature")

        channel, stats = self.run_dispatch()
        self.assertEqual(stats["raised"], 0)
        self.assertEqual(channel.sent, [])

    def test_alarms_are_grouped_into_one_message_per_tenant(self):
        self.make_alarm(alarm_type="Device Offline")
        self.make_alarm(alarm_type="High Temperature", severity="CRITICAL")

        channel, stats = self.run_dispatch()

        self.assertEqual(stats["raised"], 2)
        self.assertEqual(len(channel.sent), 1)
        self.assertIn("Новые аварии (2)", channel.sent[0][1])

    def test_a_tenant_without_telegram_is_skipped(self):
        self.configure(telegram_enabled=False)
        self.make_alarm()

        channel, stats = self.run_dispatch()
        self.assertEqual(channel.sent, [])
        self.assertEqual(stats["tenants"], 0)

    def test_a_permanent_error_is_recorded_and_not_marked_as_sent(self):
        alarm = self.make_alarm()
        channel = FakeChannel(error=TelegramAPIError(400, "chat not found"))

        _, stats = self.run_dispatch(channel)

        self.assertEqual(stats["failed"], 1)
        alarm.refresh_from_db()
        self.assertIsNone(alarm.notified_at)

        tenant = Tenant.objects.get(pk=TENANT_ID)
        self.assertEqual(tenant.additional_info[SETTINGS_KEY]["telegram_last_error"], "chat not found")

    def test_a_transient_error_leaves_the_alarm_for_the_next_tick(self):
        alarm = self.make_alarm()
        channel = FakeChannel(error=TelegramAPIError(502, "bad gateway"))

        self.run_dispatch(channel)

        alarm.refresh_from_db()
        self.assertIsNone(alarm.notified_at)
        tenant = Tenant.objects.get(pk=TENANT_ID)
        self.assertIsNone(tenant.additional_info[SETTINGS_KEY].get("telegram_last_error"))

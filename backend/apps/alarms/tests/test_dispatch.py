from datetime import timedelta

from django.core.cache import caches
from django.utils import timezone

from alarms.channels.base import ChannelNotConfigured, DeliveryError
from alarms.channels.email import EmailChannel
from alarms.channels.telegram import TelegramChannel, build_message
from alarms.models import Alarm, AlarmNotification
from alarms.notifications.dispatcher import dispatch
from alarms.notifications.settings import SETTINGS_KEY
from alarms.telegram.exceptions import TelegramAPIError, TelegramUnavailable
from alarms.tests.base import DEVICE_ID, TENANT_ID, AlarmTestCase
from main.models import Tenant


class FakeChannel(TelegramChannel):
    """The real Telegram channel minus the network."""

    def __init__(self, error=None):
        super().__init__()
        self.sent = []
        self.error = error

    def send(self, tenant, config, raised, cleared):
        if self.error:
            raise self.error
        self.sent.append((config["chat_id"], build_message(tenant, raised, cleared)))


class FakeEmailChannel(EmailChannel):
    def __init__(self, error=None):
        self.sent = []
        self.error = error

    def send(self, tenant, config, raised, cleared):
        if self.error:
            raise self.error
        self.sent.append((config["recipients"], [alarm.id for alarm in raised + cleared]))


class DispatcherTestCase(AlarmTestCase):
    def setUp(self):
        self.now = timezone.now()
        # The per-tenant rate limiter lives in Redis and outlives a test case,
        # so a run of these would otherwise throttle itself.
        caches["default"].delete_many([f"alarms:rate:{name}:{TENANT_ID}" for name in ("telegram", "email")])
        self.configure()

    def configure(self, telegram=None, email=None, **overrides):
        tenant = Tenant.objects.get(pk=TENANT_ID)
        info = tenant.additional_info or {}
        info[SETTINGS_KEY] = {
            "notify_delay_sec": 300,
            "min_severity": "MINOR",
            **overrides,
            "channels": {
                "telegram": {"enabled": True, "chat_id": "-100500", **(telegram or {})},
                "email": {"enabled": False, "recipients": [], **(email or {})},
            },
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
        stats = dispatch(now=self.now, channels=[channel])
        return channel, stats

    def mark(self, alarm, channel="telegram"):
        return AlarmNotification.objects.filter(alarm=alarm, channel=channel).first()

    def channel_settings(self, channel):
        return Tenant.objects.get(pk=TENANT_ID).additional_info[SETTINGS_KEY]["channels"][channel]


class DispatchTest(DispatcherTestCase):
    def test_an_alarm_older_than_the_delay_is_sent_once(self):
        alarm = self.make_alarm()

        channel, stats = self.run_dispatch()

        self.assertEqual(stats["raised"], 1)
        self.assertEqual(len(channel.sent), 1)
        chat_id, text = channel.sent[0]
        self.assertEqual(chat_id, "-100500")
        self.assertIn("Device Offline on DHT11", text)

        mark = self.mark(alarm)
        self.assertEqual(mark.raised_at, self.now)
        self.assertIsNone(mark.cleared_at)

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
        self.assertIsNotNone(self.mark(alarm).cleared_at)

        # And only once.
        channel, stats = self.run_dispatch()
        self.assertEqual(stats["cleared"], 0)

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
        self.configure(telegram={"enabled": False})
        self.make_alarm()

        channel, stats = self.run_dispatch()
        self.assertEqual(channel.sent, [])
        self.assertEqual(stats["tenants"], 0)

    def test_a_permanent_error_is_recorded_and_not_marked_as_sent(self):
        alarm = self.make_alarm()
        channel = FakeChannel(error=TelegramAPIError(400, "chat not found"))

        _, stats = self.run_dispatch(channel)

        self.assertEqual(stats["failed"], 1)
        self.assertIsNone(self.mark(alarm))
        self.assertEqual(self.channel_settings("telegram")["last_error"], "chat not found")

    def test_a_transient_error_leaves_the_alarm_for_the_next_tick(self):
        alarm = self.make_alarm()
        channel = FakeChannel(error=TelegramAPIError(502, "bad gateway"))

        self.run_dispatch(channel)

        self.assertIsNone(self.mark(alarm))
        self.assertIsNone(self.channel_settings("telegram").get("last_error"))

    def test_a_network_error_does_not_stop_the_tick(self):
        alarm = self.make_alarm()
        channel = FakeChannel(error=TelegramUnavailable("timed out"))

        _, stats = self.run_dispatch(channel)

        self.assertEqual(stats["failed"], 1)
        self.assertIsNone(self.mark(alarm))


class MultiChannelDispatchTest(DispatcherTestCase):
    def setUp(self):
        super().setUp()
        self.configure(email={"enabled": True, "recipients": ["ops@hotel.uz"]})

    def test_every_configured_channel_gets_the_alarm(self):
        alarm = self.make_alarm()
        telegram, email = FakeChannel(), FakeEmailChannel()

        stats = dispatch(now=self.now, channels=[telegram, email])

        self.assertEqual(stats["tenants"], 1)
        self.assertEqual(stats["raised"], 2)
        self.assertEqual(len(telegram.sent), 1)
        self.assertEqual(email.sent, [(["ops@hotel.uz"], [alarm.id])])
        self.assertEqual(
            sorted(AlarmNotification.objects.filter(alarm=alarm).values_list("channel", flat=True)),
            ["email", "telegram"],
        )

    def test_a_failing_channel_does_not_hold_back_the_other(self):
        alarm = self.make_alarm()
        telegram = FakeChannel(error=TelegramAPIError(502, "bad gateway"))
        email = FakeEmailChannel()

        dispatch(now=self.now, channels=[telegram, email])

        self.assertIsNone(self.mark(alarm, "telegram"))
        self.assertIsNotNone(self.mark(alarm, "email"))

        # Telegram recovers: it catches up, the email is not sent again.
        telegram, email = FakeChannel(), FakeEmailChannel()
        dispatch(now=self.now, channels=[telegram, email])

        self.assertEqual(len(telegram.sent), 1)
        self.assertEqual(email.sent, [])

    def test_a_clear_goes_only_to_channels_that_announced_the_raise(self):
        alarm = self.make_alarm()
        dispatch(now=self.now, channels=[FakeEmailChannel()])

        alarm.refresh_from_db()
        alarm.cleared = True
        alarm.clear_ts = self.now
        alarm.save()

        telegram, email = FakeChannel(), FakeEmailChannel()
        stats = dispatch(now=self.now, channels=[telegram, email])

        self.assertEqual(stats["cleared"], 1)
        self.assertEqual(telegram.sent, [])
        self.assertEqual(email.sent, [(["ops@hotel.uz"], [alarm.id])])

    def test_a_permanent_email_error_is_recorded_in_its_own_block(self):
        self.make_alarm()
        email = FakeEmailChannel(error=DeliveryError("SMTP refused all recipients: ops@hotel.uz", permanent=True))

        dispatch(now=self.now, channels=[FakeChannel(), email])

        self.assertEqual(self.channel_settings("email")["last_error"], "SMTP refused all recipients: ops@hotel.uz")
        self.assertIsNone(self.channel_settings("telegram").get("last_error"))

    def test_an_unconfigured_installation_skips_only_that_channel(self):
        alarm = self.make_alarm()
        email = FakeEmailChannel(error=ChannelNotConfigured("no sender"))

        stats = dispatch(now=self.now, channels=[email, FakeChannel()])

        self.assertEqual(stats["failed"], 0)
        self.assertIsNotNone(self.mark(alarm, "telegram"))
        self.assertIsNone(self.mark(alarm, "email"))

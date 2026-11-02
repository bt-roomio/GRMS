import smtplib
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.test import override_settings
from django.utils import timezone

from alarms.channels.base import ChannelNotConfigured, DeliveryError
from alarms.channels.email import EmailChannel
from alarms.models import Alarm
from alarms.tests.base import DEVICE_ID, TENANT_ID, AlarmTestCase
from main.models import Tenant

SETTINGS = {"enabled": True, "recipients": ["ops@hotel.uz", "eng@hotel.uz"], "last_error": None}
SEND = "django.core.mail.EmailMultiAlternatives.send"


@override_settings(EMAIL_HOST="smtp.example.com", DEFAULT_FROM_EMAIL="grms@example.com")
class EmailChannelTest(AlarmTestCase):
    def setUp(self):
        self.tenant = Tenant.objects.get(pk=TENANT_ID)
        start = timezone.now() - timedelta(minutes=10)
        self.alarm = Alarm.objects.create(
            tenant_id=TENANT_ID,
            originator_id=DEVICE_ID,
            alarm_type="Device Offline",
            severity="CRITICAL",
            start_ts=start,
            end_ts=start,
            details={"message": "Устройство <DHT11> не на связи"},
        )

    def test_is_configured_needs_the_switch_and_a_recipient(self):
        channel = EmailChannel()
        self.assertTrue(channel.is_configured(SETTINGS))
        self.assertFalse(channel.is_configured({**SETTINGS, "enabled": False}))
        self.assertFalse(channel.is_configured({**SETTINGS, "recipients": []}))

    def test_one_message_goes_to_every_recipient(self):
        EmailChannel().send(self.tenant, SETTINGS, [self.alarm], [])

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        assert isinstance(message, EmailMultiAlternatives)
        self.assertEqual(message.to, ["ops@hotel.uz", "eng@hotel.uz"])
        self.assertEqual(message.from_email, "grms@example.com")
        self.assertIn("новых 1", message.subject)
        self.assertIn("Новые аварии (1)", message.body)
        self.assertIn("Устройство <DHT11> не на связи", message.body)

        content, mimetype = message.alternatives[0]
        html = str(content)
        self.assertEqual(mimetype, "text/html")
        # Device names come from the field; they must not inject markup.
        self.assertIn("&lt;DHT11&gt;", html)
        self.assertIn("CRITICAL", html)

    def test_cleared_alarms_get_their_own_section(self):
        EmailChannel().send(self.tenant, SETTINGS, [], [self.alarm])

        message = mail.outbox[0]
        self.assertIn("снятых 1", message.subject)
        self.assertIn("Снятые аварии (1)", message.body)
        self.assertNotIn("Новые аварии", message.body)

    @override_settings(DEFAULT_FROM_EMAIL="", EMAIL_HOST_USER="")
    def test_no_sender_means_the_installation_is_not_configured(self):
        with self.assertRaises(ChannelNotConfigured):
            EmailChannel().send(self.tenant, SETTINGS, [self.alarm], [])
        self.assertEqual(mail.outbox, [])

    def test_refused_recipients_are_a_permanent_error(self):
        refused = smtplib.SMTPRecipientsRefused({"ops@hotel.uz": (550, b"no such user")})
        with patch(SEND, side_effect=refused), self.assertRaises(DeliveryError) as raised:
            EmailChannel().send(self.tenant, SETTINGS, [self.alarm], [])

        self.assertTrue(raised.exception.is_permanent)
        self.assertIn("ops@hotel.uz", raised.exception.description)

    def test_a_rejected_login_is_the_installations_problem(self):
        with (
            patch(SEND, side_effect=smtplib.SMTPAuthenticationError(535, b"bad credentials")),
            self.assertRaises(ChannelNotConfigured),
        ):
            EmailChannel().send(self.tenant, SETTINGS, [self.alarm], [])

    def test_a_network_error_is_transient(self):
        with patch(SEND, side_effect=TimeoutError("timed out")), self.assertRaises(DeliveryError) as raised:
            EmailChannel().send(self.tenant, SETTINGS, [self.alarm], [])

        self.assertFalse(raised.exception.is_permanent)

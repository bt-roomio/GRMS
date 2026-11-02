from datetime import timedelta
from unittest.mock import MagicMock

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from alarms.channels.base import ChannelNotConfigured, DeliveryError
from alarms.channels.whatsapp import MAX_PARAM_LENGTH, WhatsAppChannel, clean
from alarms.models import Alarm
from alarms.tests.base import DEVICE_ID, TENANT_ID, AlarmTestCase
from alarms.whatsapp.exceptions import WhatsAppAPIError, WhatsAppSenderRejected, WhatsAppUnavailable
from alarms.whatsapp.phone import mask_phone, normalize_phone
from core.utils.secrets import encrypt
from main.models import Tenant

PHONE = "998901234567"
PHONE_NUMBER_ID = "1295729336966479"


def block(**overrides) -> dict:
    """A configured channel block, the token encrypted as the settings API stores it."""
    return {
        "enabled": True,
        "recipients": [PHONE],
        "phone_number_id": PHONE_NUMBER_ID,
        "access_token": encrypt("EAAhotel"),
        "last_error": None,
        **overrides,
    }


@override_settings(WA_ALARM_TEMPLATE="alarm_summary", WA_TEMPLATE_LANGUAGE="ru")
class WhatsAppChannelTest(AlarmTestCase):
    def setUp(self):
        self.tenant = Tenant.objects.get(pk=TENANT_ID)
        self.client_factory = MagicMock()
        self.client_mock = self.client_factory.return_value
        # The channel uses the client as a context manager.
        self.client_mock.__enter__.return_value = self.client_mock
        self.channel = WhatsAppChannel(client_factory=self.client_factory)
        self.config = block()

    def make_alarm(
        self, severity="MAJOR", message="Устройство DHT11 не на связи", minutes_ago=10, alarm_type="Device Offline"
    ):
        # One active alarm per (originator, type) is a DB constraint: a second
        # one needs another type.
        start = timezone.now() - timedelta(minutes=minutes_ago)
        return Alarm.objects.create(
            tenant_id=TENANT_ID,
            originator_id=DEVICE_ID,
            alarm_type=alarm_type,
            severity=severity,
            start_ts=start,
            end_ts=start,
            details={"message": message},
        )

    def sent_params(self):
        return [call.args[3] for call in self.client_mock.send_template.call_args_list]

    def send(self, config=None, raised=None, cleared=None):
        if raised is None and cleared is None:
            raised = [self.make_alarm()]
        self.channel.send(self.tenant, config or self.config, raised or [], cleared or [])

    def test_is_configured_needs_the_switch_and_a_recipient(self):
        self.assertTrue(self.channel.is_configured(self.config))
        self.assertFalse(self.channel.is_configured(block(enabled=False)))
        self.assertFalse(self.channel.is_configured(block(recipients=[])))

    def test_every_number_is_its_own_target(self):
        targets = self.channel.targets(block(recipients=[PHONE, "998907654321"]))

        self.assertEqual([key for key, _ in targets], [f"whatsapp:{PHONE}", "whatsapp:998907654321"])
        self.assertEqual([config["recipients"] for _, config in targets], [[PHONE], ["998907654321"]])
        # The longest E.164 number still fits AlarmNotification.channel.
        self.assertLessEqual(len(self.channel.targets(block(recipients=["1" * 15]))[0][0]), 32)

    def test_the_template_goes_to_the_number(self):
        self.send()

        call = self.client_mock.send_template.call_args
        self.assertEqual(call.args[:3], (PHONE, "alarm_summary", "ru"))
        title, raised, cleared, headline = call.args[3]
        self.assertEqual(title, self.tenant.title or "GRMS")
        self.assertEqual((raised, cleared), ("1", "0"))
        self.assertIn("Устройство DHT11 не на связи", headline)

    def test_the_hotels_credentials_are_decrypted_and_the_session_closed(self):
        self.send()

        self.client_factory.assert_called_once_with(token="EAAhotel", phone_number_id=PHONE_NUMBER_ID)
        self.client_mock.__exit__.assert_called_once()

    def test_the_headline_is_the_most_severe_new_alarm(self):
        minor = self.make_alarm(severity="MINOR", message="minor one", minutes_ago=20)
        critical = self.make_alarm(
            severity="CRITICAL", message="critical one", minutes_ago=5, alarm_type="High Temperature"
        )

        self.send(raised=[minor, critical])

        headline = self.sent_params()[0][3]
        self.assertIn("critical one", headline)
        self.assertTrue(headline.startswith("🔴"))

    def test_only_cleared_alarms_get_a_resolved_headline(self):
        alarm = self.make_alarm()
        alarm.cleared = True
        alarm.clear_ts = timezone.now()

        self.send(cleared=[alarm])

        _, raised, cleared, headline = self.sent_params()[0]
        self.assertEqual((raised, cleared), ("0", "1"))
        self.assertTrue(headline.startswith("✅"))

    def test_parameters_never_carry_what_meta_rejects(self):
        self.send(raised=[self.make_alarm(message="line one\n\tline     two")])

        for param in self.sent_params()[0]:
            self.assertNotIn("\n", param)
            self.assertNotIn("\t", param)
            self.assertNotIn("     ", param)
            self.assertTrue(param)
        self.assertIn("line one line two", self.sent_params()[0][3])

    def test_a_number_not_on_whatsapp_is_a_permanent_error_naming_it(self):
        self.client_mock.send_template.side_effect = WhatsAppAPIError(400, 131026, "Message undeliverable")

        with self.assertRaises(DeliveryError) as raised:
            self.send()

        self.assertTrue(raised.exception.is_permanent)
        self.assertFalse(raised.exception.stop_channel)
        self.assertEqual(raised.exception.description, f"{PHONE}: Message undeliverable")

    def test_a_timeout_is_transient(self):
        self.client_mock.send_template.side_effect = WhatsAppUnavailable("timed out")

        with self.assertRaises(DeliveryError) as raised:
            self.send()

        self.assertFalse(raised.exception.is_permanent)
        self.assertFalse(raised.exception.stop_channel)

    def test_a_refused_token_stops_the_channel_for_this_tenant_only(self):
        self.client_mock.send_template.side_effect = WhatsAppSenderRejected("token expired")

        with self.assertRaises(DeliveryError) as raised:
            self.send()

        # Not ChannelNotConfigured: the other hotels keep their WhatsApp.
        self.assertNotIsInstance(raised.exception, ChannelNotConfigured)
        self.assertTrue(raised.exception.is_permanent)
        self.assertTrue(raised.exception.stop_channel)

    def test_without_own_credentials_nothing_is_sent(self):
        # No shared number to fall back to: a hotel never sends at roomio's expense.
        alarm = self.make_alarm()
        for config in (block(access_token=""), block(phone_number_id=""), block(phone_number_id="", access_token="")):
            with self.assertRaises(DeliveryError) as raised:
                self.send(config=config, raised=[alarm])
            self.assertTrue(raised.exception.is_permanent)
            self.assertTrue(raised.exception.stop_channel)
        self.client_factory.assert_not_called()

    def test_an_undecryptable_token_asks_to_enter_it_again(self):
        with self.assertRaises(DeliveryError) as raised:
            self.send(config=block(access_token="garbage"))

        self.assertTrue(raised.exception.is_permanent)
        self.assertIn("enter it again", raised.exception.description)


class HelpersTest(SimpleTestCase):
    def test_clean_caps_the_length_and_fills_empty_values(self):
        self.assertEqual(len(clean("x" * 1000)), MAX_PARAM_LENGTH)
        self.assertEqual(clean("  \n "), "—")

    def test_sender_rejection_cannot_disable_the_channel_for_everyone(self):
        self.assertFalse(issubclass(WhatsAppSenderRejected, ChannelNotConfigured))

    def test_normalize_phone(self):
        self.assertEqual(normalize_phone("+998 90 123-45-67"), "998901234567")
        self.assertEqual(normalize_phone("(7) 9161234567"), "79161234567")
        for bad in ("12345", "0998901234567", "+998-90-ABC", "1234567890123456"):
            self.assertIsNone(normalize_phone(bad), bad)

    def test_mask_phone(self):
        self.assertEqual(mask_phone("998901234567"), "***4567")
        self.assertEqual(mask_phone(None), "—")

from unittest.mock import MagicMock

import requests
from django.test import SimpleTestCase, override_settings

from alarms.telegram.client import TelegramClient, mask
from alarms.telegram.exceptions import (
    TelegramAPIError,
    TelegramNotConfigured,
    TelegramRateLimited,
    TelegramUnavailable,
)

TOKEN = "123456:AAH-secret-token"


def response(status_code=200, body=None, text=""):
    fake = MagicMock()
    fake.status_code = status_code
    fake.text = text
    fake.json.return_value = body if body is not None else {"ok": True, "result": {"message_id": 1}}
    return fake


@override_settings(TELEGRAM_BOT_TOKEN=TOKEN, TELEGRAM_API_URL="https://api.telegram.org", TELEGRAM_TIMEOUT=5)
class TelegramClientTest(SimpleTestCase):
    def make_client(self, session_response=None, side_effect=None):
        client = TelegramClient()
        client.session = MagicMock()
        client.session.post.return_value = session_response or response()
        if side_effect:
            client.session.post.side_effect = side_effect
        return client

    def test_missing_token_fails_early(self):
        with override_settings(TELEGRAM_BOT_TOKEN=""), self.assertRaises(TelegramNotConfigured):
            TelegramClient()

    def test_send_message_posts_to_the_bot_endpoint(self):
        client = self.make_client()
        client.send_message("-100500", "hello")

        (url,) = client.session.post.call_args.args
        self.assertEqual(url, f"https://api.telegram.org/bot{TOKEN}/sendMessage")
        payload = client.session.post.call_args.kwargs["json"]
        self.assertEqual(payload["chat_id"], "-100500")
        self.assertEqual(payload["parse_mode"], "HTML")

    def test_long_messages_are_truncated(self):
        client = self.make_client()
        client.send_message("1", "x" * 5000)
        self.assertEqual(len(client.session.post.call_args.kwargs["json"]["text"]), 4096)

    def test_rate_limit_carries_retry_after(self):
        client = self.make_client(response(429, {"ok": False, "parameters": {"retry_after": 17}}))
        with self.assertRaises(TelegramRateLimited) as raised:
            client.send_message("1", "hello")
        self.assertEqual(raised.exception.retry_after, 17)

    def test_permanent_errors_are_flagged(self):
        client = self.make_client(response(400, {"ok": False, "description": "chat not found"}))
        with self.assertRaises(TelegramAPIError) as raised:
            client.send_message("1", "hello")
        self.assertTrue(raised.exception.is_permanent)
        self.assertEqual(raised.exception.description, "chat not found")

    def test_server_errors_are_not_permanent(self):
        client = self.make_client(response(502, {"ok": False, "description": "bad gateway"}))
        with self.assertRaises(TelegramAPIError) as raised:
            client.send_message("1", "hello")
        self.assertFalse(raised.exception.is_permanent)

    def test_ok_false_with_http_200_is_still_an_error(self):
        client = self.make_client(response(200, {"ok": False, "description": "nope"}))
        with self.assertRaises(TelegramAPIError):
            client.send_message("1", "hello")

    def test_network_failure_masks_the_token(self):
        client = self.make_client(
            side_effect=requests.ConnectionError(f"https://api.telegram.org/bot{TOKEN}/sendMessage")
        )
        with self.assertRaises(TelegramUnavailable) as raised:
            client.send_message("1", "hello")
        # The token must never reach a log line or a Sentry frame.
        self.assertNotIn(TOKEN, str(raised.exception))
        self.assertIn("/bot***", str(raised.exception))


class MaskTest(SimpleTestCase):
    def test_mask_replaces_the_token_segment(self):
        self.assertEqual(
            mask("POST https://api.telegram.org/bot123:ABC/sendMessage failed"),
            "POST https://api.telegram.org/bot***/sendMessage failed",
        )

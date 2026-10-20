import hashlib
import hmac
import json

from django.test import SimpleTestCase, override_settings
from django.urls import reverse

SECRET = "app-secret"
VERIFY_TOKEN = "verify-me"


def sign(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def status_payload(status: str = "delivered") -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "statuses": [{"id": "wamid.1", "status": status, "recipient_id": "998901234567"}],
                        },
                    }
                ],
            }
        ],
    }


@override_settings(WA_VERIFY_TOKEN=VERIFY_TOKEN, WA_APP_SECRET=SECRET)
class MessengersWebhookTest(SimpleTestCase):
    url = reverse("services:messengers")

    def verify(self, **params):
        query = {"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "12345", **params}
        return self.client.get(self.url, query)

    def post(self, payload: dict, signature: str | None = None):
        body = json.dumps(payload).encode()
        headers = {"HTTP_X_HUB_SIGNATURE_256": signature if signature is not None else sign(body)}
        return self.client.post(self.url, body, content_type="application/json", **headers)

    def test_handshake_returns_bare_challenge(self):
        response = self.verify()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"12345")
        self.assertTrue(response["Content-Type"].startswith("text/plain"))

    def test_handshake_rejects_wrong_token(self):
        self.assertEqual(self.verify(**{"hub.verify_token": "nope"}).status_code, 403)

    def test_handshake_survives_non_ascii_token(self):
        self.assertEqual(self.verify(**{"hub.verify_token": "токен"}).status_code, 403)

    def test_handshake_refused_when_token_not_configured(self):
        with override_settings(WA_VERIFY_TOKEN=""):
            self.assertEqual(self.verify(**{"hub.verify_token": ""}).status_code, 403)

    def test_signed_event_is_accepted(self):
        with self.assertLogs("services.views.messengers", "INFO") as logs:
            response = self.post(status_payload())

        self.assertEqual(response.status_code, 200)
        self.assertIn("wamid.1", logs.output[0])

    def test_failed_status_is_logged_as_warning(self):
        with self.assertLogs("services.views.messengers", "WARNING") as logs:
            self.post(status_payload("failed"))

        self.assertIn("failed", logs.output[0])

    def test_logs_carry_no_phone_numbers_or_message_text(self):
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "contacts": [{"wa_id": "998901234567", "profile": {"name": "Ivan Petrov"}}],
                                "messages": [
                                    {
                                        "id": "wamid.2",
                                        "from": "998901234567",
                                        "type": "text",
                                        "text": {"body": "secret"},
                                    }
                                ],
                                "statuses": [{"id": "wamid.1", "status": "read", "recipient_id": "998901234567"}],
                            },
                        }
                    ]
                }
            ],
        }

        with self.assertLogs("services.views.messengers", "INFO") as logs:
            self.post(payload)

        output = "\n".join(logs.output)
        self.assertIn("***4567", output)
        for leaked in ("998901234567", "Ivan Petrov", "secret"):
            self.assertNotIn(leaked, output)

    def test_missing_signature_is_rejected(self):
        self.assertEqual(self.post(status_payload(), signature="").status_code, 403)

    def test_wrong_secret_is_rejected(self):
        body = json.dumps(status_payload()).encode()
        self.assertEqual(self.post(status_payload(), signature=sign(body, "other")).status_code, 403)

    def test_post_refused_when_secret_not_configured(self):
        with override_settings(WA_APP_SECRET=""):
            self.assertEqual(self.post(status_payload()).status_code, 403)

    def test_signed_garbage_is_bad_request(self):
        body = b"not json"
        response = self.client.post(
            self.url, body, content_type="application/json", HTTP_X_HUB_SIGNATURE_256=sign(body)
        )
        self.assertEqual(response.status_code, 400)

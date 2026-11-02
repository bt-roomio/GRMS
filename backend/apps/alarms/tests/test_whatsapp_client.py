from unittest.mock import MagicMock

import requests
from django.test import SimpleTestCase, override_settings

from alarms.whatsapp.client import WhatsAppClient
from alarms.whatsapp.exceptions import WhatsAppAPIError, WhatsAppSenderRejected, WhatsAppUnavailable

TOKEN = "EAAtest-token"
PHONE_NUMBER_ID = "123456789"


def response(status_code=200, body=None, text=""):
    fake = MagicMock()
    fake.status_code = status_code
    fake.text = text
    fake.json.return_value = body if body is not None else {"messages": [{"id": "wamid.ABC"}]}
    return fake


def graph_error(code, message="error", details=None, status_code=400):
    error = {"message": message, "type": "OAuthException", "code": code}
    if details:
        error["error_data"] = {"messaging_product": "whatsapp", "details": details}
    return response(status_code, {"error": error})


@override_settings(WA_GRAPH_VERSION="v21.0", WA_TIMEOUT=5)
class WhatsAppClientTest(SimpleTestCase):
    def make_client(self, session_response=None, side_effect=None):
        client = WhatsAppClient(token=TOKEN, phone_number_id=PHONE_NUMBER_ID)
        client.session = MagicMock()
        client.session.post.return_value = session_response or response()
        if side_effect:
            client.session.post.side_effect = side_effect
        return client

    def send(self, client):
        return client.send_template("998901234567", "alarm_summary", "ru", ["Hotel", "1", "0", "line"])

    def test_missing_credentials_fail_early(self):
        for token, phone_number_id in (("", PHONE_NUMBER_ID), (TOKEN, "")):
            with self.assertRaises(WhatsAppSenderRejected):
                WhatsAppClient(token=token, phone_number_id=phone_number_id)

    def test_token_goes_in_the_header_not_the_url(self):
        client = WhatsAppClient(token=TOKEN, phone_number_id=PHONE_NUMBER_ID)
        self.assertEqual(client.session.headers["Authorization"], f"Bearer {TOKEN}")
        self.assertNotIn(TOKEN, client.url)

    def test_send_template_posts_the_template_and_returns_the_wamid(self):
        client = self.make_client()

        self.assertEqual(self.send(client), "wamid.ABC")

        url = client.session.post.call_args.args[0]
        payload = client.session.post.call_args.kwargs["json"]
        self.assertEqual(url, f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages")
        self.assertEqual(payload["to"], "998901234567")
        self.assertEqual(payload["template"]["name"], "alarm_summary")
        self.assertEqual(payload["template"]["language"], {"code": "ru"})
        self.assertEqual(
            payload["template"]["components"][0]["parameters"],
            [{"type": "text", "text": text} for text in ("Hotel", "1", "0", "line")],
        )
        self.assertEqual(client.session.post.call_args.kwargs["timeout"], 5)

    def test_network_failure_is_unavailable(self):
        client = self.make_client(side_effect=requests.ConnectionError("refused"))
        with self.assertRaises(WhatsAppUnavailable):
            self.send(client)

    def test_an_expired_token_is_an_installation_problem(self):
        client = self.make_client(graph_error(190, "Error validating access token", status_code=401))
        with self.assertRaises(WhatsAppSenderRejected):
            self.send(client)

    def test_a_missing_template_is_an_installation_problem(self):
        client = self.make_client(graph_error(132001, details="template name does not exist in the translation"))
        with self.assertRaises(WhatsAppSenderRejected) as raised:
            self.send(client)
        self.assertIn("does not exist", str(raised.exception))

    def test_an_unknown_phone_number_id_is_an_installation_problem(self):
        error = graph_error(100, "Unsupported post request. Object with ID '15556518868' does not exist")
        error.json.return_value["error"]["error_subcode"] = 33
        with self.assertRaises(WhatsAppSenderRejected):
            self.send(self.make_client(error))

    def test_a_number_outside_the_allowed_list_is_permanent(self):
        client = self.make_client(graph_error(131030, details="Recipient phone number not in allowed list"))
        with self.assertRaises(WhatsAppAPIError) as raised:
            self.send(client)
        self.assertTrue(raised.exception.is_permanent)
        self.assertEqual(raised.exception.description, "Recipient phone number not in allowed list")

    def test_rate_limits_and_server_errors_are_transient(self):
        for error in (graph_error(130429, "Rate limit hit"), graph_error(1, "Unknown", status_code=500)):
            with self.assertRaises(WhatsAppAPIError) as raised:
                self.send(self.make_client(error))
            self.assertFalse(raised.exception.is_permanent)

    def test_a_non_json_error_is_still_reported(self):
        fake = response(502, text="Bad Gateway")
        fake.json.side_effect = ValueError
        with self.assertRaises(WhatsAppAPIError) as raised:
            self.send(self.make_client(fake))
        self.assertEqual(raised.exception.description, "Bad Gateway")

    def test_an_odd_error_shape_is_still_an_error_for_this_recipient(self):
        for body in ({"error": {"code": 131000, "error_data": "oops"}}, {"error": "oops"}, ["not", "a", "dict"]):
            with self.assertRaises(WhatsAppAPIError):
                self.send(self.make_client(response(400, body, text="oops")))

    def test_the_session_is_closed_on_exit(self):
        with WhatsAppClient(token=TOKEN, phone_number_id=PHONE_NUMBER_ID) as client:
            client.session = MagicMock()
        client.session.close.assert_called_once()

from unittest.mock import MagicMock, patch

import requests
from django.test import SimpleTestCase, override_settings

from fleet.netbird.client import NetBirdClient
from fleet.netbird.exceptions import NetBirdAPIError, NetBirdNotConfigured, NetBirdUnavailable

SETTINGS = {
    "NETBIRD_API_URL": "https://netbird.example.com/api",
    "NETBIRD_PAT": "nbp_test",
    "NETBIRD_TIMEOUT": 5,
    "NETBIRD_SETUP_KEY_TTL": 3600,
}


def response(status=200, payload=None, content=b"{}"):
    fake = MagicMock()
    fake.status_code = status
    fake.content = content
    fake.json.return_value = payload if payload is not None else {}
    fake.text = "error text"
    return fake


@override_settings(**SETTINGS)
class NetBirdClientTest(SimpleTestCase):
    def test_requires_configuration(self):
        with override_settings(NETBIRD_PAT=""):
            with self.assertRaises(NetBirdNotConfigured):
                NetBirdClient()

    def test_sends_token_auth_header(self):
        client = NetBirdClient()
        self.assertEqual(client.session.headers["Authorization"], "Token nbp_test")

    def test_list_peers_filters_by_group(self):
        peers = [
            {"id": "a", "groups": [{"id": "hotel"}]},
            {"id": "b", "groups": [{"id": "backend"}]},
            {"id": "c", "groups": []},
        ]
        client = NetBirdClient()
        with patch.object(client.session, "request", return_value=response(payload=peers)):
            self.assertEqual([p["id"] for p in client.list_peers(group_id="hotel")], ["a"])
            self.assertEqual(len(client.list_peers()), 3)

    def test_create_setup_key_is_single_use_and_expiring(self):
        client = NetBirdClient()
        with patch.object(client.session, "request", return_value=response(payload={"key": "K"})) as request:
            client.create_setup_key(name="node-x", auto_groups=["hotel"], usage_limit=1, expires_in=60)

        body = request.call_args.kwargs["json"]
        self.assertEqual(body["type"], "one-off")
        self.assertEqual(body["usage_limit"], 1)
        self.assertEqual(body["expires_in"], 60)
        self.assertEqual(body["auto_groups"], ["hotel"])
        self.assertFalse(body["revoked"])

    def test_http_error_becomes_api_error(self):
        client = NetBirdClient()
        failed = response(status=403, payload={"message": "forbidden"})
        with patch.object(client.session, "request", return_value=failed):
            with self.assertRaises(NetBirdAPIError) as ctx:
                client.list_peers()
        self.assertEqual(ctx.exception.status_code, 403)

    def test_network_error_becomes_unavailable(self):
        client = NetBirdClient()
        with patch.object(client.session, "request", side_effect=requests.Timeout("boom")):
            with self.assertRaises(NetBirdUnavailable):
                client.list_peers()

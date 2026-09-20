from unittest.mock import MagicMock, patch

import requests
from django.test import SimpleTestCase, override_settings

from core.utils.cloudflare import CloudflareAPIError, CloudflareClient, CloudflareNotConfigured, CloudflareUnavailable

SETTINGS = {
    "CLOUDFLARE_API_URL": "https://api.cloudflare.com/client/v4",
    "CLOUDFLARE_API_TOKEN": "cf_test",
    "CLOUDFLARE_ZONE_ID": "zone1",
    "CLOUDFLARE_TIMEOUT": 5,
}


def response(status=200, result=None, success=True, errors=None):
    fake = MagicMock()
    fake.status_code = status
    fake.json.return_value = {"success": success, "errors": errors or [], "result": result}
    fake.text = "error text"
    return fake


@override_settings(**SETTINGS)
class CloudflareClientTest(SimpleTestCase):
    def test_requires_configuration(self):
        with override_settings(CLOUDFLARE_ZONE_ID=""), self.assertRaises(CloudflareNotConfigured):
            CloudflareClient()

    def test_sends_bearer_token(self):
        client = CloudflareClient()
        self.assertEqual(client.session.headers["Authorization"], "Bearer cf_test")

    def test_zone_name(self):
        client = CloudflareClient()
        with patch.object(client.session, "request", return_value=response(result={"name": "bukhara.cloud"})) as req:
            self.assertEqual(client.zone_name(), "bukhara.cloud")
        self.assertEqual(req.call_args.args[1], "https://api.cloudflare.com/client/v4/zones/zone1")

    def test_upsert_creates_missing_record(self):
        client = CloudflareClient()
        replies = [response(result=[]), response(result={"id": "rec1"})]
        with patch.object(client.session, "request", side_effect=replies) as request:
            record = client.upsert_cname("flamingo.nodered.cloud.room.io", "api.cloud.room.io")

        self.assertEqual(record["id"], "rec1")
        method, url = request.call_args.args
        self.assertEqual((method, url), ("POST", "https://api.cloudflare.com/client/v4/zones/zone1/dns_records"))
        body = request.call_args.kwargs["json"]
        self.assertEqual(body["content"], "api.cloud.room.io")
        self.assertFalse(body["proxied"])

    def test_upsert_patches_existing_record(self):
        client = CloudflareClient()
        replies = [response(result=[{"id": "rec1"}]), response(result={"id": "rec1"})]
        with patch.object(client.session, "request", side_effect=replies) as request:
            client.upsert_cname("flamingo.nodered.cloud.room.io", "api.cloud.room.io")

        method, url = request.call_args.args
        self.assertEqual(method, "PATCH")
        self.assertTrue(url.endswith("/dns_records/rec1"))

    def test_delete_of_missing_record_is_success(self):
        client = CloudflareClient()
        reply = response(status=404, success=False, errors=[{"code": 81044, "message": "Record does not exist."}])
        with patch.object(client.session, "request", return_value=reply):
            client.delete_record("rec1")

    def test_unsuccessful_answer_raises_api_error(self):
        client = CloudflareClient()
        reply = response(status=400, success=False, errors=[{"code": 81053, "message": "Record already exists."}])
        with (
            patch.object(client.session, "request", return_value=reply),
            self.assertRaisesMessage(CloudflareAPIError, "Record already exists."),
        ):
            client.find_record("flamingo.nodered.cloud.room.io")

    def test_server_errors_and_network_failures_are_retryable(self):
        client = CloudflareClient()
        with (
            patch.object(client.session, "request", return_value=response(status=502, success=False)),
            self.assertRaises(CloudflareUnavailable),
        ):
            client.delete_record("rec1")
        with (
            patch.object(client.session, "request", side_effect=requests.ConnectionError("boom")),
            self.assertRaises(CloudflareUnavailable),
        ):
            client.delete_record("rec1")

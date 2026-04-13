from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase, override_settings

from core.utils.turnstile import TurnstileVerificationError, verify_turnstile_token


class TurnstileVerifyTests(TestCase):
    @override_settings(TURNSTILE_SECRET_KEY="test-secret-key")
    @patch("core.utils.turnstile.requests.post")
    def test_valid_token(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = verify_turnstile_token("valid-token", "1.2.3.4")

        self.assertTrue(result)
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        self.assertEqual(call_kwargs[1]["data"]["secret"], "test-secret-key")
        self.assertEqual(call_kwargs[1]["data"]["response"], "valid-token")
        self.assertEqual(call_kwargs[1]["data"]["remoteip"], "1.2.3.4")

    @override_settings(TURNSTILE_SECRET_KEY="test-secret-key")
    @patch("core.utils.turnstile.requests.post")
    def test_invalid_token(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": False,
            "error-codes": ["invalid-input-response"],
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = verify_turnstile_token("invalid-token", "1.2.3.4")

        self.assertFalse(result)

    @override_settings(TURNSTILE_SECRET_KEY="test-secret-key")
    @patch("core.utils.turnstile.requests.post")
    def test_valid_token_without_ip(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = verify_turnstile_token("valid-token")

        self.assertTrue(result)
        call_kwargs = mock_post.call_args
        self.assertNotIn("remoteip", call_kwargs[1]["data"])

    @override_settings(TURNSTILE_SECRET_KEY="")
    def test_missing_secret_key_raises(self):
        with self.assertRaises(TurnstileVerificationError):
            verify_turnstile_token("some-token")

    @override_settings(TURNSTILE_SECRET_KEY="test-secret-key")
    @patch("core.utils.turnstile.requests.post")
    def test_timeout_raises(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout()

        with self.assertRaises(TurnstileVerificationError):
            verify_turnstile_token("some-token")

    @override_settings(TURNSTILE_SECRET_KEY="test-secret-key")
    @patch("core.utils.turnstile.requests.post")
    def test_network_error_raises(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError()

        with self.assertRaises(TurnstileVerificationError):
            verify_turnstile_token("some-token")

    @override_settings(TURNSTILE_SECRET_KEY="test-secret-key")
    @patch("core.utils.turnstile.requests.post")
    def test_http_error_raises(self, mock_post):
        mock_post.side_effect = requests.exceptions.HTTPError()

        with self.assertRaises(TurnstileVerificationError):
            verify_turnstile_token("some-token")

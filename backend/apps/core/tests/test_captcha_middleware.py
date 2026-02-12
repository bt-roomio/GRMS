import json
from unittest.mock import patch

from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, TestCase, override_settings

from core.middleware.brute_force_protection import APIBruteForceProtectionMiddleware
from core.utils.turnstile import TurnstileVerificationError

CAPTCHA_BRUTE_FORCE_CONFIG = {
    "protected_endpoints": ["/api/v1/users/access-token/"],
    "max_attempts": 5,
    "lockout_duration": 900,
    "attempt_window": 300,
    "time_windows": {},
    "enable_progressive_delays": False,
    "captcha_enabled": True,
    "captcha_threshold": 3,
}


@override_settings(BRUTE_FORCE_CONFIG=CAPTCHA_BRUTE_FORCE_CONFIG, TURNSTILE_SITE_KEY="test-site-key")
class CaptchaRequirementTests(TestCase):
    """Тесты для определения необходимости CAPTCHA"""

    def setUp(self):
        self.middleware = APIBruteForceProtectionMiddleware(lambda r: HttpResponse())

    @patch("core.middleware.brute_force_protection.security_cache")
    def test_no_captcha_below_threshold(self, mock_cache):
        mock_cache.get.return_value = 2
        self.assertFalse(self.middleware._requires_captcha("1.2.3.4", "test@example.com"))

    @patch("core.middleware.brute_force_protection.security_cache")
    def test_captcha_required_at_threshold(self, mock_cache):
        mock_cache.get.return_value = 3
        self.assertTrue(self.middleware._requires_captcha("1.2.3.4", "test@example.com"))

    @patch("core.middleware.brute_force_protection.security_cache")
    def test_captcha_required_above_threshold(self, mock_cache):
        mock_cache.get.return_value = 4
        self.assertTrue(self.middleware._requires_captcha("1.2.3.4", "test@example.com"))

    @patch("core.middleware.brute_force_protection.security_cache")
    def test_no_captcha_when_disabled(self, mock_cache):
        mock_cache.get.return_value = 5
        self.middleware.captcha_enabled = False
        self.assertFalse(self.middleware._requires_captcha("1.2.3.4", "test@example.com"))


@override_settings(BRUTE_FORCE_CONFIG=CAPTCHA_BRUTE_FORCE_CONFIG, TURNSTILE_SITE_KEY="test-site-key")
class CaptchaCheckTests(TestCase):
    """Тесты для валидации CAPTCHA токена"""

    def setUp(self):
        self.middleware = APIBruteForceProtectionMiddleware(lambda r: HttpResponse())

    @patch("core.middleware.brute_force_protection.security_cache")
    def test_no_check_when_below_threshold(self, mock_cache):
        mock_cache.get.return_value = 1
        result = self.middleware._check_captcha("1.2.3.4", "test@example.com", captcha_token=None)
        self.assertIsNone(result)

    @patch("core.middleware.brute_force_protection.security_cache")
    def test_returns_403_when_no_token_provided(self, mock_cache):
        mock_cache.get.return_value = 3
        result = self.middleware._check_captcha("1.2.3.4", "test@example.com", captcha_token=None)
        self.assertIsNotNone(result)

    @patch("core.utils.turnstile.verify_turnstile_token", return_value=True)
    @patch("core.middleware.brute_force_protection.security_cache")
    def test_passes_with_valid_token(self, mock_cache, mock_verify):
        mock_cache.get.return_value = 3
        result = self.middleware._check_captcha("1.2.3.4", "test@example.com", captcha_token="valid-token")
        self.assertIsNone(result)
        mock_verify.assert_called_once_with("valid-token", remote_ip="1.2.3.4")

    @patch("core.utils.turnstile.verify_turnstile_token", return_value=False)
    @patch("core.middleware.brute_force_protection.security_cache")
    def test_returns_403_with_invalid_token(self, mock_cache, mock_verify):
        mock_cache.get.return_value = 3
        result = self.middleware._check_captcha("1.2.3.4", "test@example.com", captcha_token="invalid-token")
        self.assertIsNotNone(result)

    @patch("core.utils.turnstile.verify_turnstile_token")
    @patch("core.middleware.brute_force_protection.security_cache")
    def test_fail_open_on_infrastructure_error(self, mock_cache, mock_verify):
        """При проблемах с Cloudflare — пропускаем запрос (fail open)"""
        mock_cache.get.return_value = 3
        mock_verify.side_effect = TurnstileVerificationError("timeout")
        result = self.middleware._check_captcha("1.2.3.4", "test@example.com", captcha_token="some-token")
        self.assertIsNone(result)


@override_settings(BRUTE_FORCE_CONFIG=CAPTCHA_BRUTE_FORCE_CONFIG, TURNSTILE_SITE_KEY="test-site-key")
class CaptchaProcessRequestTests(TestCase):
    """Тесты для process_request с CAPTCHA"""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = APIBruteForceProtectionMiddleware(lambda r: HttpResponse())

    @patch("core.middleware.brute_force_protection.security_cache")
    def test_process_request_blocks_without_captcha_token(self, mock_cache):
        mock_cache.get.side_effect = lambda key, default=None: {
            # _check_lockout checks
        }.get(key, 3 if "bf:attempts:" in key else default)

        request = self.factory.post(
            "/api/v1/users/access-token/",
            data=json.dumps({"email": "test@example.com", "password": "wrong"}),
            content_type="application/json",
        )
        response = self.middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertTrue(data["captcha_required"])

    @patch("core.utils.turnstile.verify_turnstile_token", return_value=True)
    @patch("core.middleware.brute_force_protection.security_cache")
    def test_process_request_allows_with_valid_captcha(self, mock_cache, mock_verify):
        mock_cache.get.side_effect = lambda key, default=None: {}.get(key, 3 if "bf:attempts:" in key else default)

        request = self.factory.post(
            "/api/v1/users/access-token/",
            data=json.dumps({"email": "test@example.com", "password": "wrong", "captcha_token": "valid-token"}),
            content_type="application/json",
        )
        response = self.middleware.process_request(request)
        self.assertIsNone(response)

    @patch("core.middleware.brute_force_protection.security_cache")
    def test_process_request_skips_captcha_below_threshold(self, mock_cache):
        mock_cache.get.return_value = 0

        request = self.factory.post(
            "/api/v1/users/access-token/",
            data=json.dumps({"email": "test@example.com", "password": "wrong"}),
            content_type="application/json",
        )
        response = self.middleware.process_request(request)
        self.assertIsNone(response)


@override_settings(BRUTE_FORCE_CONFIG=CAPTCHA_BRUTE_FORCE_CONFIG, TURNSTILE_SITE_KEY="test-site-key")
class CaptchaProcessResponseTests(TestCase):
    """Тесты для обогащения response данными о CAPTCHA"""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = APIBruteForceProtectionMiddleware(lambda r: HttpResponse())

    @patch("core.middleware.brute_force_protection.security_cache")
    def test_response_includes_captcha_required_after_threshold(self, mock_cache):
        mock_cache.get.side_effect = lambda key, default=None: {}.get(key, 3 if "bf:attempts:" in key else default)
        mock_cache.incr.return_value = 3

        request = self.factory.post(
            "/api/v1/users/access-token/",
            data=json.dumps({"email": "test@example.com", "password": "wrong"}),
            content_type="application/json",
        )
        request._bf_ip = "1.2.3.4"
        request._bf_email = "test@example.com"

        response = JsonResponse({"detail": "Invalid credentials"}, status=401)
        result = self.middleware.process_response(request, response)

        data = json.loads(result.content)
        self.assertTrue(data["captcha_required"])
        self.assertEqual(data["captcha_site_key"], "test-site-key")

    @patch("core.middleware.brute_force_protection.security_cache")
    def test_response_no_captcha_below_threshold(self, mock_cache):
        mock_cache.get.side_effect = lambda key, default=None: {}.get(key, 1 if "bf:attempts:" in key else default)
        mock_cache.incr.return_value = 1

        request = self.factory.post(
            "/api/v1/users/access-token/",
            data=json.dumps({"email": "test@example.com", "password": "wrong"}),
            content_type="application/json",
        )
        request._bf_ip = "1.2.3.4"
        request._bf_email = "test@example.com"

        response = JsonResponse({"detail": "Invalid credentials"}, status=401)
        result = self.middleware.process_response(request, response)

        data = json.loads(result.content)
        self.assertFalse(data.get("captcha_required", False))
        self.assertNotIn("captcha_site_key", data)

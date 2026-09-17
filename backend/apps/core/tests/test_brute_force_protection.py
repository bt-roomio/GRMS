"""Regression tests for brute force protection bypasses."""

import json
import time
from unittest.mock import Mock, patch

from django.core.cache.backends.locmem import LocMemCache
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from core.middleware.brute_force_protection import APIBruteForceProtectionMiddleware
from core.utils import brute_force as bf
from core.utils.ip import get_client_ip

LOGIN = "/api/v1/users/access-token/"
SEND_LINK = "/api/v1/users/send-link/"

BF_CONFIG = {
    "protected_endpoints": [LOGIN, SEND_LINK],
    "max_attempts": 5,
    "lockout_duration": 900,
    "attempt_window": 300,
    "time_windows": {"1h": {"duration": 3600, "max_attempts": 10}},
    "enable_progressive_delays": False,
    "captcha_enabled": False,
    "whitelist_ips": [],
    "blacklist_ips": [],
}


@override_settings(BRUTE_FORCE_CONFIG=BF_CONFIG)
class BruteForceProtectionTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.cache = LocMemCache("bf-test", {})
        self.cache.clear()
        patcher = patch("core.middleware.brute_force_protection.security_cache", self.cache)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.middleware = APIBruteForceProtectionMiddleware(lambda r: HttpResponse())

    def _post(self, path, body, **meta):
        return self.factory.post(path, data=json.dumps(body), content_type="application/json", **meta)

    def _fail(self, path, email, ip="9.9.9.9", times=1):
        """Run N failed attempts through the full middleware cycle."""
        for _ in range(times):
            request = self._post(path, {"email": email}, REMOTE_ADDR=ip)
            assert self.middleware.process_request(request) is None
            self.middleware.process_response(request, JsonResponse({"detail": "bad"}, status=401))

    def _attempts(self, path, email, ip="9.9.9.9"):
        return self.cache.get(bf.key("attempts", path, email, ip), 0)

    # --- IP spoofing through headers ---

    def test_xff_cannot_override_remote_addr(self):
        """The leftmost X-Forwarded-For entry is client-controlled and must not be used."""
        request = self.factory.post(LOGIN, HTTP_X_FORWARDED_FOR="127.0.0.1", REMOTE_ADDR="9.9.9.9")
        self.assertEqual(get_client_ip(request), "9.9.9.9")

    @override_settings(BRUTE_FORCE_CONFIG={**BF_CONFIG, "whitelist_ips": ["127.0.0.1"]})
    def test_spoofed_xff_does_not_reach_whitelist(self):
        middleware = APIBruteForceProtectionMiddleware(lambda r: HttpResponse())
        request = self._post(LOGIN, {"email": "a@b.com"}, HTTP_X_FORWARDED_FOR="127.0.0.1", REMOTE_ADDR="9.9.9.9")
        middleware.process_request(request)
        # The IP did not reach the whitelist, so attempt tracking is on
        self.assertEqual(request._bf_ip, "9.9.9.9")

    # --- Per-endpoint counter isolation ---

    def test_send_link_success_does_not_reset_login_counter(self):
        self._fail(LOGIN, "victim@x.com", times=4)
        self.assertEqual(self._attempts(LOGIN, "victim@x.com"), 4)

        # A successful send-link for the same email must not lift the login limit
        request = self._post(SEND_LINK, {"email": "victim@x.com"}, REMOTE_ADDR="9.9.9.9")
        self.middleware.process_request(request)
        self.middleware.process_response(request, HttpResponse(b"Email sent"))

        self.assertEqual(self._attempts(LOGIN, "victim@x.com"), 4)

    def test_fifth_failure_triggers_lockout(self):
        self._fail(LOGIN, "victim@x.com", times=5)
        request = self._post(LOGIN, {"email": "victim@x.com"}, REMOTE_ADDR="9.9.9.9")
        response = self.middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 429)

    # --- Email normalization ---

    def test_email_case_variants_share_one_counter(self):
        self._fail(LOGIN, "victim@x.com", times=2)
        self._fail(LOGIN, "VICTIM@X.com", times=2)
        self._fail(LOGIN, "  Victim@x.COM  ", times=1)
        self.assertEqual(self._attempts(LOGIN, "victim@x.com"), 5)

    def test_blank_email_does_not_disable_tracking(self):
        for raw in ("", None):
            self.cache.clear()
            request = self._post(LOGIN, {"email": raw}, REMOTE_ADDR="9.9.9.9")
            self.middleware.process_request(request)
            self.middleware.process_response(request, JsonResponse({"detail": "bad"}, status=401))
            self.assertEqual(self._attempts(LOGIN, "anonymous"), 1, f"email={raw!r} was not counted")

    def test_form_encoded_body_is_parsed(self):
        request = self.factory.post(LOGIN, data={"email": "Victim@X.com"}, REMOTE_ADDR="9.9.9.9")
        self.middleware.process_request(request)
        self.assertEqual(request._bf_email, "victim@x.com")

    # --- Counter reset ---

    def test_success_clears_extended_window(self):
        self._fail(LOGIN, "victim@x.com", times=3)
        window_key = bf.window_key("1h", LOGIN, "victim@x.com", "9.9.9.9")
        self.assertTrue(self.cache.get(window_key))

        request = self._post(LOGIN, {"email": "victim@x.com"}, REMOTE_ADDR="9.9.9.9")
        self.middleware.process_request(request)
        self.middleware.process_response(request, JsonResponse({"ok": True}, status=200))

        self.assertIsNone(self.cache.get(window_key))
        self.assertEqual(self._attempts(LOGIN, "victim@x.com"), 0)

    # --- Progressive delay does not block a worker thread ---

    @override_settings(BRUTE_FORCE_CONFIG={**BF_CONFIG, "enable_progressive_delays": True})
    def test_progressive_delay_expires_and_never_sleeps(self):
        """
        The delay must be measured from the last failure instead of lasting the
        whole attempt_window: one typo means ~1 second of waiting, not 5 minutes.
        """
        middleware = APIBruteForceProtectionMiddleware(lambda r: HttpResponse())
        body = {"email": "victim@x.com"}

        # The first failure goes through and sets the delay
        request = self._post(LOGIN, body, REMOTE_ADDR="9.9.9.9")
        with patch("core.middleware.brute_force_protection.time.sleep") as sleeper:
            self.assertIsNone(middleware.process_request(request))
            middleware.process_response(request, JsonResponse({"detail": "bad"}, status=401))

            # An immediate retry is rejected, but with a short Retry-After
            request = self._post(LOGIN, body, REMOTE_ADDR="9.9.9.9")
            response = middleware.process_request(request)

        sleeper.assert_not_called()
        self.assertEqual(response.status_code, 429)
        retry_after = int(response["Retry-After"])
        self.assertGreater(retry_after, 0)
        self.assertLessEqual(retry_after, 2, "the delay must not stretch across the whole attempt_window")

        # Once the deadline has passed the request goes through again
        key = bf.key("next_allowed", LOGIN, "victim@x.com", "9.9.9.9")
        self.cache.set(key, time.time() - 1, 300)
        request = self._post(LOGIN, body, REMOTE_ADDR="9.9.9.9")
        self.assertIsNone(middleware.process_request(request))

    @override_settings(BRUTE_FORCE_CONFIG={**BF_CONFIG, "enable_progressive_delays": True})
    def test_progressive_delay_grows_with_failures(self):
        middleware = APIBruteForceProtectionMiddleware(lambda r: HttpResponse())
        key = bf.key("next_allowed", LOGIN, "victim@x.com", "9.9.9.9")
        deadlines = []

        for _ in range(3):
            self.cache.delete(key)  # drop the delay so the attempt goes through
            request = self._post(LOGIN, {"email": "victim@x.com"}, REMOTE_ADDR="9.9.9.9")
            middleware.process_request(request)
            middleware.process_response(request, JsonResponse({"detail": "bad"}, status=401))
            deadlines.append(self.cache.get(key) - time.time())

        self.assertLess(deadlines[0], deadlines[1])
        self.assertLess(deadlines[1], deadlines[2])

    # --- Counter atomicity ---

    def test_counter_creates_key_with_atomic_add(self):
        """
        The counter must start with add() (SETNX in Redis) rather than incr()
        with key creation in an except branch. The old pattern lost up to 3/4 of
        the increments under concurrent attempts and let the limit be bypassed
        with plain concurrency. LocMemCache serializes operations with a lock,
        so the race is caught by call order rather than by load.
        """
        cache = Mock()
        cache.add.return_value = True  # the key was missing, add created it

        count = bf.incr_with_ttl(cache, "bf:attempts:x", 300, sliding=True)

        self.assertEqual(count, 1)
        cache.add.assert_called_once()
        cache.incr.assert_not_called()

    def test_counter_increments_existing_key(self):
        cache = Mock()
        cache.add.return_value = False  # the key already exists
        cache.incr.return_value = 4

        count = bf.incr_with_ttl(cache, "bf:attempts:x", 300, sliding=True)

        self.assertEqual(count, 4)
        cache.incr.assert_called_once()
        cache.touch.assert_called_once()  # a sliding window extends the TTL

    def test_counter_survives_key_expiring_between_add_and_incr(self):
        cache = Mock()
        cache.add.side_effect = [False, True]  # existed, but expired before incr
        cache.incr.side_effect = ValueError("key not found")

        self.assertEqual(bf.incr_with_ttl(cache, "bf:attempts:x", 300), 1)

    def test_extended_window_ttl_is_not_extended(self):
        """
        The 1h window must expire an hour after the first attempt. Extending the
        TTL would turn it into a permanent lockout for an active client.
        """
        cache = Mock()
        cache.add.return_value = False
        cache.incr.return_value = 2

        bf.incr_with_ttl(cache, "bf:window:1h:x", 3600)

        cache.touch.assert_not_called()

    # --- Protection scope ---

    def test_unprotected_path_is_ignored(self):
        request = self._post("/api/v1/main/rooms/", {"email": "a@b.com"}, REMOTE_ADDR="9.9.9.9")
        self.assertIsNone(self.middleware.process_request(request))
        self.assertFalse(hasattr(request, "_bf_ip"))

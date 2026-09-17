"""
Redis-based brute force protection for the REST API
"""

import json
import logging
import math
import time

from django.conf import settings
from django.core.cache import caches
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from core.utils import brute_force as bf
from core.utils.ip import get_client_ip

# Logger "security" rather than __name__: __name__ resolves to `core.middleware.…`,
# which LOGGING routes through the `core` logger with propagate=False, so lockout
# records never reached the security handler.
logger = logging.getLogger("security")

security_cache = caches["security"]


class APIBruteForceProtectionMiddleware(MiddlewareMixin):
    """
    Middleware protecting API endpoints from brute force attacks.

    The state of an (endpoint, email, ip) triple is two keys: a failure counter
    and the instant until which attempts are rejected. That instant serves both
    the progressive delay and the full lockout — they answer the same question,
    "when is it allowed again".

    Counters are isolated per endpoint: a success on one protected route does
    not reset the limits of another.
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
        self.config = getattr(settings, "BRUTE_FORCE_CONFIG", {})

        self.protected_endpoints = set(self.config.get("protected_endpoints", []))

        self.max_attempts = self.config.get("max_attempts", 5)
        self.lockout_duration = self.config.get("lockout_duration", 900)  # 15 minutes
        self.attempt_window = self.config.get("attempt_window", 300)  # 5 minutes

        # 429 (throttle) counts as a failure: otherwise an attacker stays below
        # the lockout threshold by interleaving throttled requests.
        self.failure_statuses = frozenset(self.config.get("failure_statuses", (401, 403, 429)))
        self.success_statuses = frozenset(self.config.get("success_statuses", (200, 201)))

        self.time_windows = self.config.get(
            "time_windows",
            {
                "1h": {"duration": 3600, "max_attempts": 10},
                "24h": {"duration": 86400, "max_attempts": 30},
            },
        )

        self.enable_progressive_delays = self.config.get("enable_progressive_delays", True)
        self.base_delay = self.config.get("base_delay", 0.5)
        self.max_delay = self.config.get("max_delay", 30)

        self.captcha_enabled = self.config.get("captcha_enabled", False)
        self.captcha_threshold = self.config.get("captcha_threshold", 3)

        self.whitelist_ips = set(self.config.get("whitelist_ips", []))
        self.blacklist_ips = set(self.config.get("blacklist_ips", []))

    def process_request(self, request):
        if not self._should_protect(request):
            return None

        ip = get_client_ip(request)
        scope = request.path

        if ip in self.whitelist_ips:
            return None

        if ip in self.blacklist_ips:
            logger.warning(f"Blacklisted IP blocked: {ip} (path: {scope})")
            return self._blocked_response("IP blacklisted")

        body_data = self._parse_request_body(request)
        email = self._extract_email(body_data)

        is_blocked, reason, retry_after = self._check_lockout(scope, ip, email)
        if is_blocked:
            logger.warning(f"Blocked request: {request.method} {scope} from {ip} (email: {email}) - {reason}")
            response = self._blocked_response(reason)
            if retry_after:
                response["Retry-After"] = str(retry_after)
            return response

        if self.captcha_enabled:
            captcha_response = self._check_captcha(ip, email, body_data.get("captcha_token"), scope)
            if captcha_response is not None:
                return captcha_response

        request._bf_ip = ip
        request._bf_email = email

        return None

    def process_response(self, request, response):
        if not self._should_protect(request):
            return response

        ip = getattr(request, "_bf_ip", None)
        email = getattr(request, "_bf_email", None)
        if not ip or not email:
            return response

        scope = request.path

        if response.status_code in self.failure_statuses:
            attempt_count = self._record_failed_attempt(scope, ip, email)
            self._annotate_response(response, attempt_count)
        elif response.status_code in self.success_statuses:
            self._reset_attempts(scope, ip, email)

        return response

    def _should_protect(self, request) -> bool:
        return request.method == "POST" and request.path in self.protected_endpoints

    def _extract_email(self, body_data: dict) -> str:
        """
        Pull the email out of the body and normalize it.

        Normalization is mandatory: the login and password-reset serializers call
        email.lower() before authenticating, so without it Victim@x.com and
        victim@x.com would produce different keys and independent attempt budgets.
        An empty/None value collapses to "anonymous", otherwise a falsy email
        would silently disable attempt tracking in process_response.
        """
        raw = body_data.get("email")
        if not isinstance(raw, str):
            return "anonymous"
        return raw.strip().lower() or "anonymous"

    def _parse_request_body(self, request) -> dict:
        try:
            content_type = (request.content_type or "").lower()

            if content_type.startswith("application/json"):
                return json.loads(request.body) if request.body else {}

            # DRF accepts form data by default: without this branch every
            # form-encoded login would collapse into the shared "anonymous" bucket.
            if content_type.startswith(("application/x-www-form-urlencoded", "multipart/form-data")):
                return request.POST.dict()
        except Exception:
            logger.debug("Failed to parse request body for brute force tracking", exc_info=True)

        return {}

    def _check_lockout(self, scope: str, ip: str, email: str) -> tuple[bool, str, int]:
        """Returns: (is_blocked, reason, retry_after_seconds)"""
        # Set by clear_brute_force --hard-block
        if security_cache.get(bf.hard_block_key(ip)):
            return True, "IP permanently blocked", 0

        # One deadline covers both the progressive delay and a full lockout
        next_allowed = security_cache.get(bf.key("next_allowed", scope, email, ip))
        if next_allowed:
            remaining = next_allowed - time.time()
            if remaining > 0:
                seconds = math.ceil(remaining)
                return True, f"Too many attempts. Retry in {seconds} seconds", seconds

        for window_name, window_config in self.time_windows.items():
            count = security_cache.get(bf.window_key(window_name, scope, email, ip), 0)
            if count >= window_config["max_attempts"]:
                logger.critical(
                    f"Extended window limit exceeded: {count} attempts in {window_name} for {email} from {ip}"
                )
                return True, f"Too many attempts in {window_name} period", 0

        return False, "", 0

    # ==========================================
    # CAPTCHA (Cloudflare Turnstile)
    # ==========================================

    def _requires_captcha(self, ip: str, email: str, scope: str = "") -> bool:
        if not self.captcha_enabled:
            return False
        return security_cache.get(bf.key("attempts", scope, email, ip), 0) >= self.captcha_threshold

    def _check_captcha(self, ip: str, email: str, captcha_token: str | None = None, scope: str = ""):
        """
        Validate the CAPTCHA token when one is required.

        Returns None when no CAPTCHA is required or the token is valid.
        Returns JsonResponse when a CAPTCHA is required but missing/invalid.
        """
        if not self._requires_captcha(ip, email, scope):
            return None

        if not captcha_token:
            logger.warning(f"CAPTCHA required but not provided: {email} from {ip}")
            return self._captcha_response(
                "CAPTCHA required",
                "Too many failed attempts. Please complete the CAPTCHA challenge.",
            )

        from core.utils.turnstile import TurnstileVerificationError, verify_turnstile_token

        try:
            is_valid = verify_turnstile_token(captcha_token, remote_ip=ip)
        except TurnstileVerificationError:
            # Fail open on infrastructure trouble — brute force protection is still active
            logger.error(f"Turnstile verification failed (infrastructure), allowing request: {email} from {ip}")
            return None

        if not is_valid:
            logger.warning(f"Invalid CAPTCHA token: {email} from {ip}")
            return self._captcha_response("Invalid CAPTCHA", "CAPTCHA verification failed. Please try again.")

        return None

    def _captcha_response(self, error: str, detail: str) -> JsonResponse:
        return JsonResponse(
            {
                "error": error,
                "detail": detail,
                "captcha_required": True,
                "captcha_site_key": getattr(settings, "TURNSTILE_SITE_KEY", ""),
            },
            status=403,
        )

    def _record_failed_attempt(self, scope: str, ip: str, email: str) -> int:
        """Returns the current attempt count."""
        now = time.time()

        # Sliding counting window: the TTL is extended on every failure.
        attempt_count = bf.incr_with_ttl(
            security_cache,
            bf.key("attempts", scope, email, ip),
            self.attempt_window,
            sliding=True,
        )

        # Extended windows are counters with a fixed TTL (it must not be extended,
        # otherwise the window never expires and turns into a permanent lockout).
        for window_name, window_config in self.time_windows.items():
            bf.incr_with_ttl(
                security_cache,
                bf.window_key(window_name, scope, email, ip),
                window_config["duration"],
            )

        # One deadline covers both cases: the limit is reached — full lockout,
        # otherwise an exponential delay. The TTL equals the pause, so the key expires on its own.
        if attempt_count >= self.max_attempts:
            block_for = self.lockout_duration
            logger.critical(f"LOCKOUT TRIGGERED: {email} from {ip} - {attempt_count} failed attempts")
        elif self.enable_progressive_delays:
            block_for = min(self.base_delay * (2**attempt_count), self.max_delay)
        else:
            block_for = 0

        if block_for:
            security_cache.set(
                bf.key("next_allowed", scope, email, ip),
                now + block_for,
                math.ceil(block_for) + 1,
            )

        # Reverse email -> IP index: without it the admin API has nothing to unlock,
        # since the lockout keys include the IP and the administrator does not know it.
        bf.remember_ip(email, ip, cache=security_cache)

        logger.warning(f"Failed login attempt #{attempt_count}: {email} from {ip} (path: {scope})")

        return attempt_count

    def _reset_attempts(self, scope: str, ip: str, email: str):
        keys = [
            *(bf.key(kind, scope, email, ip) for kind in bf.KINDS),
            # Windows too: without them a level-3 block cannot be lifted — the user
            # cannot get a 200 while blocked, and the key lives until its TTL.
            *(bf.window_key(name, scope, email, ip) for name in self.time_windows),
        ]
        security_cache.delete_many(keys)

        logger.info(f"Successful login: {email} from {ip} - counters reset")

    def _annotate_response(self, response, attempt_count: int) -> None:
        if not response.get("Content-Type", "").startswith("application/json"):
            return

        try:
            data = json.loads(response.content)
            data["attempts_left"] = max(0, self.max_attempts - attempt_count)
            data["lockout_duration"] = self.lockout_duration

            if self.captcha_enabled:
                requires_captcha = attempt_count >= self.captcha_threshold
                data["captcha_required"] = requires_captcha
                if requires_captcha:
                    data["captcha_site_key"] = getattr(settings, "TURNSTILE_SITE_KEY", "")

            response.content = json.dumps(data).encode()
        except Exception:
            logger.exception("Failed to enrich brute force response body")

    def _blocked_response(self, reason: str) -> JsonResponse:
        return JsonResponse({"error": "Access denied", "detail": reason, "status": "blocked"}, status=429)

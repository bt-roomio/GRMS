import os
from typing import Any

TURNSTILE_ENABLED = os.getenv("TURNSTILE_ENABLED", "False").lower() in ("true", "1", "yes")
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "")
TURNSTILE_SITE_KEY = os.getenv("TURNSTILE_SITE_KEY", "")
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
TURNSTILE_TIMEOUT = 5  # seconds


def _ip_list(env_name: str) -> list[str]:
    """Read a comma-separated IP list from an environment variable."""
    return [ip.strip() for ip in os.getenv(env_name, "").split(",") if ip.strip()]


BRUTE_FORCE_CONFIG: dict[str, Any] = {
    "protected_endpoints": [
        "/api/v1/users/access-token/",
        "/api/v1/users/refresh-token/",
    ],
    "max_attempts": 5,
    "lockout_duration": 900,  # 15 minutes of lockout
    "attempt_window": 300,  # 5 minutes to count attempts (do NOT lower: 10s makes lockout unreachable)
    "time_windows": {
        "1h": {
            "duration": 3600,
            "max_attempts": 10,
        },
        "24h": {
            "duration": 86400,
            "max_attempts": 30,
        },
    },
    "enable_progressive_delays": True,
    "base_delay": 0.5,
    "max_delay": 30,
    "captcha_threshold": 3,
    "captcha_enabled": TURNSTILE_ENABLED,
    "whitelist_ips": _ip_list("BRUTE_FORCE_WHITELIST_IPS"),
    "blacklist_ips": _ip_list("BRUTE_FORCE_BLACKLIST_IPS"),
}

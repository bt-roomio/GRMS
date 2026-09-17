"""Client IP resolution behind a reverse proxy."""

import os

from django.conf import settings

# Headers we trust, in priority order. Configurable through the environment
# because the proxy chain depends on the deployment: with Cloudflare in front
# it is CF-Connecting-IP, without it only X-Real-IP set by our own nginx.
#
# X-Forwarded-For is deliberately absent from the default: nginx-proxy builds
# it with `$proxy_add_x_forwarded_for`, appending the real IP at the END, so
# the leftmost entry is fully client-controlled and must never be read.
#
# IMPORTANT: every header listed here must be unconditionally overwritten by a
# trusted proxy. If Cloudflare is not in the chain, CF-Connecting-IP has to be
# removed from the list — otherwise a client can forge any address.
DEFAULT_TRUSTED_IP_HEADERS = ("HTTP_CF_CONNECTING_IP", "HTTP_X_REAL_IP")


def _configured_headers() -> tuple[str, ...]:
    configured = getattr(settings, "TRUSTED_IP_HEADERS", None)
    if configured is None:
        return DEFAULT_TRUSTED_IP_HEADERS
    return tuple(configured)


def trusted_ip_headers_from_env(env_name: str = "TRUSTED_IP_HEADERS") -> tuple[str, ...]:
    """
    Read the header list from the environment ("CF-Connecting-IP,X-Real-IP").

    An empty value means "trust REMOTE_ADDR only" — the correct choice when the
    application faces the network directly.
    """
    raw = os.getenv(env_name)
    if raw is None:
        return DEFAULT_TRUSTED_IP_HEADERS

    headers = []
    for item in raw.split(","):
        name = item.strip().upper().replace("-", "_")
        if not name:
            continue
        headers.append(name if name.startswith("HTTP_") else f"HTTP_{name}")
    return tuple(headers)


def get_client_ip(request) -> str:
    """Return the client IP that can be trusted for rate limiting."""
    for header in _configured_headers():
        value = request.META.get(header)
        if value:
            # Take the first entry in case a proxy sent a list: a trusted header
            # holds a single address, but the safeguard is cheap.
            return value.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR", "unknown")

"""
Cloudflare Turnstile CAPTCHA verification utility.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger("security")


class TurnstileVerificationError(Exception):
    """Raised when Turnstile verification fails due to infrastructure issues."""

    pass


def verify_turnstile_token(token: str, remote_ip: str | None = None) -> bool:
    """
    Verify a Cloudflare Turnstile token via the siteverify API.

    Args:
        token: The turnstile response token from the client.
        remote_ip: Optional client IP for additional validation.

    Returns:
        True if the token is valid, False otherwise.

    Raises:
        TurnstileVerificationError: If the API call fails (network error, timeout, missing config).
    """
    secret_key = getattr(settings, "TURNSTILE_SECRET_KEY", "")
    verify_url = getattr(settings, "TURNSTILE_VERIFY_URL", "https://challenges.cloudflare.com/turnstile/v0/siteverify")
    timeout = getattr(settings, "TURNSTILE_TIMEOUT", 5)

    if not secret_key:
        logger.error("TURNSTILE_SECRET_KEY is not configured")
        raise TurnstileVerificationError("Turnstile secret key not configured")

    payload = {
        "secret": secret_key,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        response = requests.post(verify_url, data=payload, timeout=timeout)
        response.raise_for_status()
        result = response.json()

        success = result.get("success", False)

        if not success:
            error_codes = result.get("error-codes", [])
            logger.warning(f"Turnstile verification failed: {error_codes} (IP: {remote_ip})")

        return success

    except requests.exceptions.Timeout:
        logger.error(f"Turnstile verification timed out (IP: {remote_ip})")
        raise TurnstileVerificationError("Turnstile verification timed out")
    except requests.exceptions.RequestException as e:
        logger.error(f"Turnstile verification request failed: {e} (IP: {remote_ip})")
        raise TurnstileVerificationError(f"Turnstile verification failed: {e}")

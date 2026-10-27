import re

SEPARATORS = re.compile(r"[\s\-().]")
# Country code first, no leading zero, at most 15 digits.
E164_DIGITS = re.compile(r"[1-9]\d{7,14}")


def normalize_phone(raw: str) -> str | None:
    """
    E.164 digits without "+" — what the Cloud API expects in ``to`` — or None
    when ``raw`` is not a phone number in international format.
    """
    digits = SEPARATORS.sub("", raw).removeprefix("+")
    return digits if E164_DIGITS.fullmatch(digits) else None


def mask_phone(phone: str | None) -> str:
    """For logs: enough to tell numbers apart, not enough to call them."""
    if not phone:
        return "—"
    return f"***{phone[-4:]}"

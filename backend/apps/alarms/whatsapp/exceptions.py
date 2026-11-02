from alarms.channels.base import DeliveryError

# Graph API error codes, https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes
# The sender itself is refused: token, permissions, the template. Every
# recipient would get the same answer.
SENDER_ERROR_CODES = frozenset(
    {
        0,  # AuthException
        3,  # API method not permitted for the app
        10,  # permission denied
        190,  # access token expired or invalid
        132000,  # template parameter count mismatch
        132001,  # template does not exist in this language
        132005,  # translated text too long
        132007,  # template format character policy violated
        132012,  # template parameter format mismatch
        132015,  # template paused
        132016,  # template disabled
    }
)
# This one recipient will never get it: the tenant has to fix the number.
RECIPIENT_ERROR_CODES = frozenset(
    {
        131026,  # message undeliverable — not a WhatsApp number, outdated client
        131030,  # recipient not in the allowed list (test number)
    }
)


class WhatsAppError(Exception):
    """Base class for every failure talking to the WhatsApp Cloud API."""


class WhatsAppSenderRejected(WhatsAppError):
    """
    Credentials missing, or Meta refused the sender itself — expired token,
    missing permission, unknown phone number id, template not approved.

    Deliberately not a ``ChannelNotConfigured``: the sender is always one
    hotel's own number, and if this ever escaped ``WhatsAppChannel`` the
    dispatcher would switch WhatsApp off for every other hotel too.
    """


class WhatsAppUnavailable(WhatsAppError, DeliveryError):
    """Network-level failure — timeout, DNS, connection refused."""


class WhatsAppAPIError(WhatsAppError, DeliveryError):
    """Graph API answered with an error about this one recipient, or a transient one."""

    def __init__(self, status_code: int, code: int | None, description: str, payload: dict | None = None):
        super().__init__(f"WhatsApp API {status_code} ({code}): {description}")
        self.status_code = status_code
        self.code = code
        self.description = description
        self.payload = payload or {}

    @property
    def is_permanent(self) -> bool:
        return self.code in RECIPIENT_ERROR_CODES

"""
Symmetric encryption for third-party secrets kept in JSON settings blocks.

``Tenant.additional_info`` is returned whole by the tenant API, so a token
stored there in clear text would be readable by anyone who can list tenants.

The key is ``SECRETS_ENCRYPTION_KEY`` when set, otherwise derived from
``SECRET_KEY`` — rotating the latter without setting the former makes every
stored secret undecryptable, and its owner has to enter it again.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class SecretDecryptionError(Exception):
    """The ciphertext was made with another key, or is not ciphertext at all."""


def fernet() -> Fernet:
    key = settings.SECRETS_ENCRYPTION_KEY
    if not key:
        # A purpose prefix so this key is never the raw SECRET_KEY reused.
        digest = hashlib.sha256(f"grms.secrets:{settings.SECRET_KEY}".encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key)


def encrypt(value: str) -> str:
    return fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    try:
        return fernet().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError) as exc:
        raise SecretDecryptionError("stored secret cannot be decrypted with the current key") from exc

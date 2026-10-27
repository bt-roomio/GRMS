import logging
from typing import Any

import requests
from django.conf import settings

from alarms.whatsapp.exceptions import (
    SENDER_ERROR_CODES,
    WhatsAppAPIError,
    WhatsAppSenderRejected,
    WhatsAppUnavailable,
)

logger = logging.getLogger(__name__)

GRAPH_URL = "https://graph.facebook.com"


class WhatsAppClient:
    """
    One call, ``POST /<phone_number_id>/messages`` with a template. Free text is
    only allowed within 24 hours of the recipient's last message, which an
    alarm can never count on, so templates are the whole surface.
    """

    def __init__(
        self, token: str, phone_number_id: str, graph_version: str | None = None, timeout: float | None = None
    ):
        # Credentials always come from the tenant's settings: there is no
        # installation-wide sender (see alarms.channels.whatsapp).
        self.token = token
        self.phone_number_id = phone_number_id
        self.graph_version = graph_version or settings.WA_GRAPH_VERSION
        self.timeout = timeout if timeout is not None else settings.WA_TIMEOUT

        if not self.token or not self.phone_number_id:
            raise WhatsAppSenderRejected("token and phone_number_id are required")

        self.session = requests.Session()
        # In a header, not the URL, so the token never lands in a log line.
        self.session.headers["Authorization"] = f"Bearer {self.token}"

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "WhatsAppClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    @property
    def url(self) -> str:
        return f"{GRAPH_URL}/{self.graph_version}/{self.phone_number_id}/messages"

    def send_template(self, to: str, name: str, language: str, params: list[str]) -> str:
        """Returns the ``wamid`` that delivery statuses on the webhook refer to."""
        template: dict[str, Any] = {"name": name, "language": {"code": language}}
        if params:
            # A template without variables must not carry an empty body
            # component — Meta counts it as a parameter mismatch (132000).
            template["components"] = [{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}]

        payload = {"messaging_product": "whatsapp", "to": to, "type": "template", "template": template}

        try:
            response = self.session.post(self.url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            raise WhatsAppUnavailable(f"POST {self.url} failed: {exc}") from exc

        try:
            body: Any = response.json()
        except ValueError:
            body = {}

        if response.status_code >= 400 or "error" in body:
            raise error_from(response.status_code, body, response.text)

        try:
            return body["messages"][0]["id"]
        except (KeyError, IndexError, TypeError):
            # Accepted, just without the id we expected; nothing to retry.
            logger.warning("WhatsApp accepted a message to %s without a wamid: %s", to, body)
            return ""


def error_from(status_code: int, body: dict, text: str) -> Exception:
    # Every level checked: an odd shape from Meta or a proxy must still become
    # an error for this recipient, not an AttributeError that ends the tick.
    error = body.get("error") if isinstance(body, dict) else None
    error = error if isinstance(error, dict) else {}
    code = error.get("code")
    error_data = error.get("error_data")
    details = error_data.get("details") if isinstance(error_data, dict) else None
    description = str(details or error.get("message") or text[:255])

    # 100/33: the phone number id does not exist or the token cannot see it —
    # typically the phone number itself entered instead of its id.
    unknown_object = code == 100 and error.get("error_subcode") == 33
    if status_code == 401 or code in SENDER_ERROR_CODES or unknown_object:
        return WhatsAppSenderRejected(f"WhatsApp API {status_code} ({code}): {description}")
    return WhatsAppAPIError(status_code, code, description, body)

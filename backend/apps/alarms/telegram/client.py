import logging
import re
from typing import Any

import requests
from django.conf import settings

from alarms.telegram.exceptions import (
    TelegramAPIError,
    TelegramNotConfigured,
    TelegramRateLimited,
    TelegramUnavailable,
)

logger = logging.getLogger(__name__)

# The token sits in the path, so any unmasked URL in a log line or a Sentry
# frame leaks the bot outright.
TOKEN_IN_URL = re.compile(r"/bot[^/]+")

MAX_MESSAGE_LENGTH = 4096


def mask(text: str) -> str:
    return TOKEN_IN_URL.sub("/bot***", text)


class TelegramClient:
    """
    One call, ``sendMessage``. That is the whole surface the dispatcher needs,
    which is why there is no ``python-telegram-bot`` dependency here.
    """

    def __init__(self, token: str | None = None, base_url: str | None = None, timeout: float | None = None):
        self.token = token if token is not None else settings.TELEGRAM_BOT_TOKEN
        self.base_url = (base_url if base_url is not None else settings.TELEGRAM_API_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.TELEGRAM_TIMEOUT

        if not self.token:
            raise TelegramNotConfigured("TELEGRAM_BOT_TOKEN must be set to send alarm notifications")

        self.session = requests.Session()

    def _request(self, method: str, payload: dict) -> Any:
        url = f"{self.base_url}/bot{self.token}/{method}"

        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            raise TelegramUnavailable(f"POST {mask(url)} failed: {mask(str(exc))}") from exc

        try:
            body = response.json()
        except ValueError:
            body = {}

        if response.status_code == 429:
            raise TelegramRateLimited(int(body.get("parameters", {}).get("retry_after", 30)))

        if response.status_code >= 400 or not body.get("ok", False):
            description = body.get("description") or mask(response.text)
            raise TelegramAPIError(response.status_code, description, body)

        return body.get("result")

    def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> Any:
        return self._request(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text[:MAX_MESSAGE_LENGTH],
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
        )

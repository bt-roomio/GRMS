class TelegramError(Exception):
    """Base class for every failure talking to the Telegram Bot API."""


class TelegramNotConfigured(TelegramError):
    """TELEGRAM_BOT_TOKEN missing from the environment."""


class TelegramUnavailable(TelegramError):
    """Network-level failure — timeout, DNS, connection refused."""


class TelegramAPIError(TelegramError):
    """The Bot API answered, but not with success."""

    def __init__(self, status_code, description, payload=None):
        self.status_code = status_code
        self.description = description
        self.payload = payload or {}
        super().__init__(f"Telegram API {status_code}: {description}")

    @property
    def is_permanent(self) -> bool:
        """
        A wrong chat id or a blocked bot will never succeed on a retry — the
        tenant has to fix it, so the dispatcher records it instead of looping.
        """
        return self.status_code in (400, 401, 403, 404)


class TelegramRateLimited(TelegramError):
    """429 — retry after the interval the API asked for."""

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Telegram rate limited, retry after {retry_after}s")

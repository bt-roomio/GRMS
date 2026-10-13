from typing import Protocol


class NotificationChannel(Protocol):
    """
    One delivery method — the pared-down stand-in for TB's Notification Center.

    Telegram is the one this task needs; email (``EMAIL_*`` is already
    configured in this project) and webhooks are a file each, added the day
    someone asks.
    """

    name: str

    def is_configured(self, tenant_settings: dict) -> bool: ...

    def send(self, tenant_settings: dict, text: str) -> None: ...

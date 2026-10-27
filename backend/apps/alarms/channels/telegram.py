import html
from typing import Any, ClassVar

from alarms.notifications.message import (
    CLEARED_TITLE,
    RAISED_TITLE,
    alarm_lines,
    overflow,
    tenant_title,
    timezone_offset,
)
from alarms.telegram.client import TelegramClient


class TelegramChannel:
    name: ClassVar[str] = "telegram"
    defaults: ClassVar[dict[str, Any]] = {"enabled": False, "chat_id": "", "last_error": None}

    def __init__(self, client: TelegramClient | None = None):
        # Built lazily so a tenant with no Telegram configured never forces the
        # bot token to exist.
        self._client = client

    @property
    def client(self) -> TelegramClient:
        if self._client is None:
            self._client = TelegramClient()
        return self._client

    def is_configured(self, config: dict) -> bool:
        return bool(config.get("enabled") and config.get("chat_id"))

    def targets(self, config: dict) -> list[tuple[str, dict]]:
        # One message for the whole block.
        return [(self.name, config)]

    def send(self, tenant, config: dict, raised: list, cleared: list) -> None:
        self.client.send_message(str(config["chat_id"]), build_message(tenant, raised, cleared))


def build_message(tenant, raised: list, cleared: list) -> str:
    offset = timezone_offset(tenant)
    parts = [f"<b>{html.escape(tenant_title(tenant))}</b>"]

    for title, alarms, is_raised in ((RAISED_TITLE, raised, True), (CLEARED_TITLE, cleared, False)):
        if not alarms:
            continue
        parts.append("")
        parts.append(f"<b>{title} ({len(alarms)})</b>")
        for line in alarm_lines(alarms, offset, raised=is_raised):
            where = f" · {html.escape(line.room)}" if line.room else ""
            parts.append(f"{line.icon} {line.time}{where} — {html.escape(line.text)}")
        if more := overflow(alarms):
            parts.append(more)

    return "\n".join(parts)

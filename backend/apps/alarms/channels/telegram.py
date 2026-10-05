from alarms.telegram.client import TelegramClient


class TelegramChannel:
    name = "telegram"

    def __init__(self, client: TelegramClient | None = None):
        # Built lazily so a tenant with no Telegram configured never forces the
        # bot token to exist.
        self._client = client

    @property
    def client(self) -> TelegramClient:
        if self._client is None:
            self._client = TelegramClient()
        return self._client

    def is_configured(self, tenant_settings: dict) -> bool:
        return bool(tenant_settings.get("telegram_enabled") and tenant_settings.get("telegram_chat_id"))

    def send(self, tenant_settings: dict, text: str) -> None:
        self.client.send_message(str(tenant_settings["telegram_chat_id"]), text)

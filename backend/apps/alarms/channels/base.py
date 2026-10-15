from typing import TYPE_CHECKING, Any, ClassVar, Protocol

if TYPE_CHECKING:
    from alarms.models import Alarm
    from main.models import Tenant


class ChannelNotConfigured(Exception):
    """
    The installation, not the tenant, is missing something (bot token, SMTP
    sender, rejected SMTP login): every tenant would hit the same wall, so the
    dispatcher skips the channel for the rest of the tick.
    """


class DeliveryError(Exception):
    """The channel answered, but the message did not go out."""

    def __init__(self, description: str, permanent: bool = False):
        super().__init__(description)
        self.description = description
        self.permanent = permanent

    @property
    def is_permanent(self) -> bool:
        """
        Will never succeed on a retry — the tenant has to fix its settings, so
        the dispatcher records it on the tenant instead of only logging it.
        """
        return self.permanent


class NotificationChannel(Protocol):
    """
    One delivery method — the pared-down stand-in for TB's Notification Center.

    Every channel is self-contained: its settings are its own block under
    ``notification_settings["channels"][name]``, and what it already announced
    is its own ``AlarmNotification`` rows, so a mail server being down never
    holds back Telegram and never makes it repeat itself.
    """

    name: ClassVar[str]
    # The channel's settings block as an unconfigured tenant sees it. Every
    # channel has ``enabled`` and ``last_error`` — the latter is written by the
    # dispatcher when the channel rejects the tenant's settings for good.
    defaults: ClassVar[dict[str, Any]]

    def is_configured(self, config: dict) -> bool: ...

    def send(self, tenant: "Tenant", config: dict, raised: list["Alarm"], cleared: list["Alarm"]) -> None: ...

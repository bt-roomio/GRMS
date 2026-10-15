"""
Every channel the dispatcher knows, in delivery order.

Adding a sender is a class here plus its settings serializer in
``main/serializers/notification_settings.py`` — no column, no migration.
"""

from alarms.channels.base import NotificationChannel
from alarms.channels.email import EmailChannel
from alarms.channels.telegram import TelegramChannel

CHANNELS: tuple[type[NotificationChannel], ...] = (TelegramChannel, EmailChannel)


def default_channels() -> list[NotificationChannel]:
    return [channel() for channel in CHANNELS]

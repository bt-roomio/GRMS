from rest_framework import serializers

from alarms.constants import AlarmSeverity
from alarms.notifications.settings import (
    CHANNELS_KEY,
    DEFAULTS,
    SETTINGS_KEY,
    channel_blocks,
    notification_settings,
    stored_settings,
)


class ChannelSettingsSerializer(serializers.Serializer):
    """What every channel block has: a switch and the last permanent error."""

    enabled = serializers.BooleanField(required=False)
    # Set by the dispatcher, never by the client.
    last_error = serializers.CharField(read_only=True, allow_null=True)


class TelegramSettingsSerializer(ChannelSettingsSerializer):
    chat_id = serializers.CharField(max_length=64, required=False, allow_blank=True)

    class Meta:
        ref_name = "TelegramNotificationSettings"


class EmailSettingsSerializer(ChannelSettingsSerializer):
    recipients = serializers.ListField(child=serializers.EmailField(max_length=254), max_length=20, required=False)

    class Meta:
        ref_name = "EmailNotificationSettings"

    def validate_recipients(self, value):
        # The same address twice would get every message twice.
        return list(dict.fromkeys(address.lower() for address in value))


class ChannelsSerializer(serializers.Serializer):
    """One field per channel in ``alarms.channels.registry.CHANNELS``."""

    telegram = TelegramSettingsSerializer(required=False)
    email = EmailSettingsSerializer(required=False)

    class Meta:
        ref_name = "NotificationChannels"


class NotificationSettingsSerializer(serializers.Serializer):
    """
    Singleton resource over ``Tenant.additional_info["notification_settings"]``,
    the same pattern as ``AlarmSettingsSerializer``.

    The top level is shared by every channel; ``channels`` holds one block per
    channel, merged key by key on PUT so a client may send only what changed.
    """

    tenant_id = serializers.UUIDField(source="id", read_only=True)
    notify_delay_sec = serializers.IntegerField(required=False, min_value=0, max_value=86400)
    min_severity = serializers.ChoiceField(choices=AlarmSeverity.choices, required=False)
    channels = ChannelsSerializer(required=False)

    class Meta:
        ref_name = "NotificationSettings"

    def update(self, instance, validated_data):
        updated_by = validated_data.pop("updated_by", None)
        channels_data = validated_data.pop(CHANNELS_KEY, None) or {}

        stored = stored_settings(instance)
        stored.update({key: value for key, value in validated_data.items() if key in DEFAULTS})

        stored_channels = channel_blocks(stored)
        for name, changes in channels_data.items():
            block = {**(stored_channels.get(name) or {}), **changes}
            # Any edit of a channel deserves a clean slate: the old "chat not
            # found" must not keep haunting the settings screen. If it is still
            # wrong, the next tick writes it back.
            block["last_error"] = None
            stored_channels[name] = block
        stored[CHANNELS_KEY] = stored_channels

        additional_info = instance.additional_info if isinstance(instance.additional_info, dict) else {}
        additional_info[SETTINGS_KEY] = stored
        instance.additional_info = additional_info

        if updated_by is not None:
            instance.updated_by = updated_by
        instance.save()
        return instance

    def to_representation(self, instance):
        return {"tenant_id": instance.id, **notification_settings(instance)}

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
from alarms.whatsapp.phone import normalize_phone
from core.utils.secrets import encrypt


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


class WhatsAppSettingsSerializer(ChannelSettingsSerializer):
    # Phone numbers in international format; stored as E.164 digits without
    # "+", which is what the Cloud API expects in "to".
    recipients = serializers.ListField(child=serializers.CharField(max_length=32), max_length=20, required=False)
    # The hotel's own sender — required: there is no shared number to fall back to.
    phone_number_id = serializers.RegexField(r"^\d{5,32}$", required=False, allow_blank=True)
    # Stored encrypted and never returned; an empty string removes it.
    access_token = serializers.CharField(max_length=1024, required=False, allow_blank=True, write_only=True)
    has_access_token = serializers.BooleanField(read_only=True)

    class Meta:
        ref_name = "WhatsAppNotificationSettings"

    def validate_access_token(self, value):
        value = value.strip()
        return encrypt(value) if value else ""

    def validate_recipients(self, value):
        numbers = []
        for raw in value:
            phone = normalize_phone(raw)
            if phone is None:
                raise serializers.ValidationError(f"{raw!r} is not a phone number in international format")
            numbers.append(phone)
        # The same number twice would pay for every message twice.
        return list(dict.fromkeys(numbers))


class ChannelsSerializer(serializers.Serializer):
    """One field per channel in ``alarms.channels.registry.CHANNELS``."""

    telegram = TelegramSettingsSerializer(required=False)
    whatsapp = WhatsAppSettingsSerializer(required=False)
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

    def validate(self, attrs):
        whatsapp = (attrs.get(CHANNELS_KEY) or {}).get("whatsapp")
        if whatsapp is not None and self.instance is not None:
            # Checked against the merged block: the credentials may have been
            # saved by an earlier PUT.
            stored = channel_blocks(stored_settings(self.instance)).get("whatsapp") or {}
            block = {**stored, **whatsapp}
            if block.get("enabled") and not (block.get("phone_number_id") and block.get("access_token")):
                raise serializers.ValidationError(
                    {CHANNELS_KEY: {"whatsapp": {"enabled": ["phone_number_id and access_token are required"]}}}
                )
        return attrs

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
        data = notification_settings(instance)
        whatsapp = data[CHANNELS_KEY].get("whatsapp")
        if whatsapp is not None:
            # Not even the ciphertext leaves the server; the screen only needs
            # to know whether one is set.
            whatsapp["has_access_token"] = bool(whatsapp.pop("access_token", ""))
        return {"tenant_id": instance.id, **data}

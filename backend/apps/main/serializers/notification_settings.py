from rest_framework import serializers

from alarms.constants import AlarmSeverity
from alarms.notifications.settings import DEFAULTS, SETTINGS_KEY


class NotificationSettingsSerializer(serializers.Serializer):
    """
    Singleton resource over ``Tenant.additional_info["notification_settings"]``,
    the same pattern as ``AlarmSettingsSerializer``.
    """

    telegram_enabled = serializers.BooleanField(default=False)
    telegram_chat_id = serializers.CharField(
        max_length=64, required=False, allow_blank=True, allow_null=True, default=""
    )
    # Set by the dispatcher, never by the client.
    telegram_last_error = serializers.CharField(read_only=True, allow_null=True)
    notify_delay_sec = serializers.IntegerField(default=300, min_value=0, max_value=86400)
    min_severity = serializers.ChoiceField(choices=AlarmSeverity.choices, default=AlarmSeverity.MINOR)

    class Meta:
        ref_name = "NotificationSettings"

    def update(self, instance, validated_data):
        updated_by = validated_data.pop("updated_by", None)

        additional_info = instance.additional_info if isinstance(instance.additional_info, dict) else {}
        stored = additional_info.get(SETTINGS_KEY) or {}
        stored = {**DEFAULTS, **stored, **validated_data}

        if "telegram_chat_id" in validated_data:
            # A new chat deserves a clean slate: the old "chat not found" must
            # not keep haunting the settings screen.
            stored["telegram_last_error"] = None

        additional_info[SETTINGS_KEY] = stored
        instance.additional_info = additional_info

        if updated_by is not None:
            instance.updated_by = updated_by
        instance.save()
        return instance

    def to_representation(self, instance):
        additional_info = instance.additional_info if isinstance(instance.additional_info, dict) else {}
        stored = additional_info.get(SETTINGS_KEY) or {}
        return {"tenant_id": instance.id, **DEFAULTS, **stored}

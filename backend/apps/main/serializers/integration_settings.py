from rest_framework import serializers

from main.models import Device


class IntegrationSettingsSerializer(serializers.Serializer):
    PMS_type = serializers.ChoiceField(choices=("FIAS",), default=None, allow_null=True)
    integration_device = serializers.PrimaryKeyRelatedField(
        queryset=Device.objects.all(), default=None, allow_null=True
    )
    is_active = serializers.BooleanField(default=None, allow_null=True)

    def validate(self, attrs):
        attrs["integration_device"] = str(attrs["integration_device"].id) if attrs.get("integration_device") else None
        return super().validate(attrs)

    def update(self, instance, validated_data):
        additional_info = instance.additional_info or {}
        i_settings = additional_info.get("integration_settings", {})
        i_settings = {**i_settings, **validated_data}
        additional_info["integration_settings"] = i_settings
        instance.additional_info = additional_info
        instance.save()
        return instance

    def to_representation(self, instance):
        i_settings = instance.additional_info.get("integration_settings", {}) if instance.additional_info else {}
        for field_name, field in self.fields.items():
            if field_name == "main_dashboard":
                i_settings[field_name] = i_settings.get(field_name, None)
            elif field_name == "public_space_dashboard":
                i_settings[field_name] = i_settings.get(field_name, None)
            elif field_name == "door_lock":
                i_settings[field_name] = i_settings.get(field_name, field.to_representation(field.get_default()))
            else:
                i_settings[field_name] = i_settings.get(field_name, field.default)

        merged = {**i_settings}
        return {"tenant_id": instance.id, **merged}

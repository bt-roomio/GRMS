from rest_framework import serializers

from main.models import Device


class HotezaSerializer(serializers.Serializer):
    hotel_id = serializers.CharField(required=False, default="", allow_blank=True)
    enable = serializers.BooleanField(default=False)


class MewsSerializer(serializers.Serializer):
    hotel_id = serializers.CharField(required=False, default="", allow_blank=True)
    enable = serializers.BooleanField(default=False)
    send_tasks = serializers.BooleanField(default=False)
    client_token = serializers.CharField(required=False, default="", allow_blank=True)
    access_token = serializers.CharField(required=False, default="", allow_blank=True)
    roomio_access_control = serializers.BooleanField(default=False)


class IntegrationSettingsSerializer(serializers.Serializer):
    hoteza = HotezaSerializer(required=False, default={"hotel_id": "", "enable": False})
    mews = MewsSerializer(required=False, default={"hotel_id": "", "enable": False, "send_tasks": False})
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

        result = {}
        for field_name, field in self.fields.items():
            stored_value = i_settings.get(field_name)
            if isinstance(field, serializers.Serializer):
                default_data = field.to_representation(field.get_default())
                if isinstance(stored_value, dict):
                    merged_data = {**default_data, **stored_value}
                else:
                    merged_data = default_data

                result[field_name] = merged_data
            elif field_name == "main_dashboard":
                result[field_name] = stored_value if stored_value is not None else None
            elif field_name == "public_space_dashboard":
                result[field_name] = stored_value if stored_value is not None else None
            elif field_name == "door_lock":
                result[field_name] = (
                    stored_value if stored_value is not None else field.to_representation(field.get_default())
                )
            else:
                result[field_name] = stored_value if stored_value is not None else field.default

        return {"tenant_id": instance.id, **result}

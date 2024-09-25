from rest_framework import serializers


class AlarmSettingsSerializer(serializers.Serializer):
    bathroom_enable = serializers.BooleanField(required=False)
    humidity_enable = serializers.BooleanField(required=False)

    def update(self, instance, validated_data):
        instance.additional_info = {
            "general_settings": {
                **(instance.additional_info and instance.additional_info.get("general_settings", {}) or {}),
            }
        }

        if "bathroom_enable" in self.initial_data:
            instance.additional_info["general_settings"]["bathroom_enable"] = validated_data["bathroom_enable"]

        if "humidity_enable" in self.initial_data:
            instance.additional_info["general_settings"]["humidity_enable"] = validated_data["humidity_enable"]
        instance.save()
        return instance

    def to_representation(self, instance):
        general_settings = instance.additional_info and instance.additional_info.get("general_settings", {}) or {}
        return {
            "tenant_id": instance.id,
            "bathroom_enable": general_settings.get("bathroom_enable"),
            "humidity_enable": general_settings.get("humidity_enable"),
        }

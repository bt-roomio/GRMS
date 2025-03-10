from rest_framework import serializers

from main.models import AdminSettings


class JsonValueSerializer(serializers.Serializer):
    hoteza_whitelist = serializers.ListField(child=serializers.CharField(), allow_empty=False, required=True)


class AdminSettingsSerializer(serializers.ModelSerializer):
    json_value = JsonValueSerializer(default={"hoteza_whitelist": []})

    def to_representation(self, instance):
        if not instance.json_value.get("hoteza_whitelist"):
            instance.json_value["hoteza_whitelist"] = []
        return super().to_representation(instance)

    class Meta:
        model = AdminSettings
        fields = ("id", "key", "json_value", "tenant")
        extra_kwargs = {"key": {"required": False}, "json_value": {"required": True}, "tenant": {"required": False}}

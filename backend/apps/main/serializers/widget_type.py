from core.utils.serializers import ValidatorSerializer
from main.models import WidgetType
from rest_framework import serializers


class WidgetTypeSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        tenant = validated_data.get("tenant")
        name = validated_data.get("name")
        widget_type = WidgetType.objects.filter(tenant=tenant, name=name)

        if widget_type.exists():
            raise serializers.ValidationError({"detail": "A widget type with this name already exists!"})

        return super().create(validated_data)

    def update(self, instance, validated_data):
        widget_type = WidgetType.objects.filter(tenant=instance.tenant, name=validated_data.get("name"))
        if instance.name != validated_data.get("name") and widget_type.exists():
            raise serializers.ValidationError({"detail": "A widget type with this name already exists!"})
        return super().update(instance, validated_data)

    class Meta:
        model = WidgetType
        fields = (
            "id",
            "created_at",
            "name",
            "deprecated",
            "fqn",
            "descriptor",
            "image",
            "description",
            "tags",
            "external_id",
        )


class WidgetTypeFilterParams(ValidatorSerializer):
    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)

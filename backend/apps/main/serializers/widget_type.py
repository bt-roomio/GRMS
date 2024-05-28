from rest_framework import serializers

from main.models import WidgetType


class WidgetTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WidgetType
        fields = (
            "id",
            "created_at",
            "name",
            "tenant",
            "deprecated",
            "fqn",
            "descriptor",
            "image",
            "description",
            "tags",
            "external_id",
        )

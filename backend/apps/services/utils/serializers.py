from rest_framework import serializers
from rest_framework.fields import DateTimeField


class MillisecondDateTimeField(DateTimeField):
    def to_representation(self, value):
        formatted = super().to_representation(value)
        if isinstance(formatted, str) and "." in formatted:
            seconds, microseconds = formatted.split(".")
            ms = microseconds[:3]
            formatted = f"{seconds}{ms}"
        return formatted


class BaseModelSerializer(serializers.ModelSerializer):
    created_at = MillisecondDateTimeField(read_only=True)
    updated_at = MillisecondDateTimeField(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    updated_by = serializers.PrimaryKeyRelatedField(read_only=True)

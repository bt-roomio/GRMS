from rest_framework import serializers
from services.models import Integration


class IntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integration
        fields = (
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "name",
            "type",
            "description",
            "additional_info",
            "enable",
            "is_active",
            "tenant",
        )
        extra_kwargs = {
            "tenant": {"required": False, "allow_null": True},
            "is_active": {"read_only": True},
        }

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
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
            "enable": {"read_only": True},
        }


class IntegrationParams(ValidatorSerializer):
    SORT_FIELDS = ("created_at", "-created_at", "name", "-name", "type", "-type")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("name", "type"), required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)

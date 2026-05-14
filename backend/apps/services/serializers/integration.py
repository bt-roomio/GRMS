from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from core.utils.serializers import ValidatorSerializer
from services.models import Integration, Integrator


class IntegrationSerializer(serializers.ModelSerializer):
    integrator = serializers.SlugRelatedField(slug_field="name", queryset=Integrator.objects.all())

    class Meta:
        model = Integration
        fields = (
            "id",
            "integrator",
            "hotel_id",
            "description",
            "access_token",
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
        validators = [
            UniqueTogetherValidator(
                queryset=Integration.objects.filter(is_active=True),
                fields=("integrator", "tenant"),
                message="Integration with this integrator already exists for this tenant.",
            )
        ]


class IntegrationParams(ValidatorSerializer):
    SORT_FIELDS = ("created_at", "-created_at", "name", "-name")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("name",), required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)

from typing import ClassVar

from rest_framework import serializers

from services.models import Integration, Integrator


class IntegrationSerializer(serializers.ModelSerializer):
    integrator = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        # Distinct from services.IntegrationSerializer, which drf-yasg would otherwise clash with.
        ref_name = "AdminIntegration"
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
            "created_at",
            "updated_at",
        )
        read_only_fields = tuple(field for field in fields if field != "enable")


class CreateIntegrationSerializer(serializers.ModelSerializer):
    integrator = serializers.SlugRelatedField(slug_field="name", queryset=Integrator.objects.all())

    class Meta:
        model = Integration
        fields = ("integrator", "hotel_id", "description", "access_token", "additional_info", "enable")
        extra_kwargs: ClassVar = {"enable": {"default": True}}

    def validate_integrator(self, value):
        """The unique constraint would raise a 500; a duplicate is a client error."""
        taken = Integration.objects.filter(
            tenant=self.context["tenant"],
            integrator=value,
            is_active=True,
        ).exists()
        if taken:
            raise serializers.ValidationError("Integration with this integrator already exists for this tenant.")
        return value


class IntegrationToggleSerializer(serializers.ModelSerializer):
    enable = serializers.BooleanField(required=True)

    class Meta:
        model = Integration
        fields = ("enable",)

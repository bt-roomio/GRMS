from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import TenantGroup
from main.services.tenant_provisioning import provision_tenant_group
from users.models import User


class TenantGroupFilterParams(ValidatorSerializer):
    sort_by = serializers.ListField(
        child=serializers.ChoiceField(
            choices=["-created_at", "created_at", "title", "-title"],
            default="-created_at",
        ),
        required=False,
    )
    search_field = serializers.ChoiceField(choices=("title",), required=False)
    search_value = serializers.CharField(required=False)
    page = serializers.IntegerField(default=1, min_value=1)
    size = serializers.IntegerField(default=50, max_value=200)


class TenantGroupSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["tenants_count"] = getattr(instance, "tenants_count", 0)
        return data

    class Meta:
        model = TenantGroup
        fields = ("id", "created_at", "title", "description", "is_active", "additional_info")


class CreateTenantGroupSerializer(serializers.ModelSerializer):
    """Creates the chain and, in the same transaction, the superuser pinned to it."""

    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True)

    def validate_title(self, value):
        if TenantGroup.objects.filter(title__iexact=value).exists():
            raise serializers.ValidationError(f"Tenant group with title '{value}' already exists.")
        return value

    def validate_email(self, value):
        normalized = value.lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError(f"User with email '{normalized}' already exists.")
        return normalized

    def create(self, validated_data):
        return provision_tenant_group(**validated_data)

    class Meta:
        model = TenantGroup
        fields = ("id", "title", "description", "is_active", "additional_info", "email", "password")


class UpdateTenantGroupSerializer(serializers.ModelSerializer):
    def validate_title(self, value):
        if TenantGroup.objects.filter(title__iexact=value).exclude(pk=self.instance.pk).exists():  # ty: ignore
            raise serializers.ValidationError(f"Tenant group with title '{value}' already exists.")
        return value

    class Meta:
        model = TenantGroup
        fields = ("title", "description", "is_active", "additional_info")

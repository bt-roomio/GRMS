from datetime import datetime

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Permission
from django.db import transaction

from rest_framework import serializers

from core.utils.constants import UI_PERMISSIONS
from core.utils.serializers import ValidatorSerializer
from main.models import DeviceProfile, Tenant, TenantProfile
from users.models import Role, User


class TenantFilterParams(ValidatorSerializer):
    sort_by = serializers.ListField(
        child=serializers.ChoiceField(
            choices=[
                "-created_at",
                "created_at",
                "title",
                "-title",
            ],
            default="-created_at",
        ),
        required=False,
    )
    search_field = serializers.ChoiceField(choices=("title",), required=False)
    search_value = serializers.CharField(required=False)


class TenantSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        instance.created_at = (
            datetime.fromtimestamp(instance.created_at / 1000)
            if isinstance(instance.created_at, int)
            else instance.created_at
        )
        data = super().to_representation(instance)

        data["online_rooms"] = instance.online_rooms if hasattr(instance, "online_rooms") else 0
        data["offline_rooms"] = instance.offline_rooms if hasattr(instance, "offline_rooms") else 0
        data["total_rooms"] = instance.total_rooms if hasattr(instance, "total_rooms") else 0
        data["offline_gateways"] = instance.offline_gateways if hasattr(instance, "offline_gateways") else 0
        data["total_gateways"] = instance.total_gateways if hasattr(instance, "total_gateways") else 0
        return data

    class Meta:
        model = Tenant
        fields = (
            "id",
            "created_at",
            "title",
            "email",
            "tenant_profile",
            "additional_info",
            "address",
            "address2",
            "city",
            "country",
            "phone",
            "region",
            "state",
            "zip",
        )


class UpdateTenantSerializer(serializers.ModelSerializer):
    def validate_title(self, value):
        if Tenant.objects.filter(title__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError(f"Tenant with title '{value}' already exists.")
        return value

    class Meta:
        model = Tenant
        fields = (
            "title",
            "email",
            "phone",
            "address",
            "address2",
            "city",
            "country",
            "region",
            "state",
            "zip",
            "additional_info",
            "tenant_profile",
        )


class CreateTenantSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        normalized = value.lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError(f"User with email '{normalized}' already exists.")
        return normalized

    def validate_title(self, value):
        if Tenant.objects.filter(title__iexact=value).exists():
            raise serializers.ValidationError(f"Tenant with title '{value}' already exists.")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            tenant_profile, _ = TenantProfile.objects.get_or_create(name="Default", defaults={"is_default": True})
            tenant = Tenant.objects.create(tenant_profile=tenant_profile, title=validated_data["title"])
            Tenant.objects.get_or_create(tenant_profile=tenant_profile, title="Default")

            role, _ = Role.objects.get_or_create(name="TENANT_ADMIN", tenant=tenant)
            role.permissions.add(*Permission.objects.all())
            role.additional_info = {"ui_permissions": UI_PERMISSIONS}
            role.save()

            user = User.objects.create(
                tenant=tenant,
                email=validated_data["email"],
                password=make_password(validated_data["password"]),
            )
            user.roles.add(role)

            for name in ["Default", "Integration Devices", "Card Reader"]:
                DeviceProfile.objects.get_or_create(name=name, tenant=tenant, type="DEFAULT")

        return tenant

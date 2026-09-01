from datetime import UTC, datetime
from typing import ClassVar

from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from core.utils.serializers import ValidatorSerializer
from main.models import Device, Tenant, TenantGroup
from main.services.tenant_provisioning import provision_tenant
from users.models import User


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
    group = serializers.UUIDField(required=False)
    page = serializers.IntegerField(default=1, min_value=1)
    size = serializers.IntegerField(default=50, min_value=1, max_value=500)


def _serialize_gateways(instance):
    """Строит список gateway-устройств тенанта для представления сериализатора.

    Ожидает, что instance.gateways проставлен через prefetch_related(Prefetch("device_set", ..., "gateways")).
    """
    if not hasattr(instance, "gateways"):
        return None
    return [
        {
            "id": gateway.id,
            "name": gateway.name,
            "status": gateway.status,
            "is_gateway": gateway.additional_info.get("gateway", False),
            "excluded_monitoring": gateway.additional_info.get("excluded_monitoring", False),
        }
        for gateway in instance.gateways
    ]


class TenantSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        instance.created_at = (
            datetime.fromtimestamp(instance.created_at / 1000, tz=UTC)
            if isinstance(instance.created_at, int)
            else instance.created_at
        )
        data = super().to_representation(instance)

        data["online_rooms"] = instance.online_rooms if hasattr(instance, "online_rooms") else 0
        data["offline_rooms"] = instance.offline_rooms if hasattr(instance, "offline_rooms") else 0
        data["total_rooms"] = instance.total_rooms if hasattr(instance, "total_rooms") else 0
        data["offline_gateways"] = instance.offline_gateways if hasattr(instance, "offline_gateways") else 0
        data["total_gateways"] = instance.total_gateways if hasattr(instance, "total_gateways") else 0
        gateways = _serialize_gateways(instance)
        if gateways is not None:
            data["gateways"] = gateways
        data["group_title"] = instance.group.title if instance.group_id else None
        return data

    class Meta:
        model = Tenant
        fields = (
            "id",
            "created_at",
            "title",
            "group",
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


class UpdateGatewaySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    excluded_monitoring = serializers.BooleanField()


class UpdateTenantSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        gateways = _serialize_gateways(instance)
        if gateways is not None:
            data["gateways"] = gateways
        return data

    gateways = UpdateGatewaySerializer(many=True, write_only=True, required=False)

    def validate_title(self, value):
        if Tenant.objects.filter(title__iexact=value).exclude(pk=self.instance.pk).exists():  # ty: ignore
            raise serializers.ValidationError(f"Tenant with title '{value}' already exists.")
        return value

    def validate_group(self, value):
        """A chain admin may only park hotels in their own chain."""
        request = self.context.get("request")
        pinned = request.user.tenant_group_id if request else None
        if pinned and (value is None or value.pk != pinned):
            raise serializers.ValidationError("You can only manage hotels of your own chain.")
        return value

    def update(self, instance, validated_data):
        gateways = validated_data.pop("gateways", None)
        instance = super().update(instance, validated_data)

        cached_gateways = {gateway.id: gateway for gateway in getattr(instance, "gateways", [])}
        for gateway_data in gateways or []:
            device = cached_gateways.get(gateway_data["id"]) or get_object_or_404(
                Device,
                id=gateway_data["id"],
                tenant=instance,
                is_active=True,
                additional_info__gateway=True,
            )
            device.additional_info = device.additional_info or {}
            device.additional_info["excluded_monitoring"] = gateway_data["excluded_monitoring"]
            device.save(update_fields=["additional_info"])

        return instance

    class Meta:
        model = Tenant
        fields = (
            "title",
            "group",
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
            "gateways",
        )
        extra_kwargs: ClassVar[dict[str, dict[str, bool]]] = {
            "additional_info": {"read_only": True},
        }


class CreateTenantSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    group = serializers.PrimaryKeyRelatedField(queryset=TenantGroup.objects.all(), required=False, allow_null=True)

    def validate(self, attrs):
        email, title = attrs.get("email"), attrs.get("title")

        normalized = email.lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError(f"User with email '{normalized}' already exists.")

        if Tenant.objects.filter(title__iexact=title).exists():
            raise serializers.ValidationError(f"Tenant with title '{title}' already exists.")

        return attrs

    def create(self, validated_data):
        return provision_tenant(**validated_data)

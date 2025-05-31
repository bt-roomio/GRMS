from rest_framework import serializers

from core.utils.random_letter import get_random_letter
from core.utils.serializers import ValidatorSerializer
from main.models import Device, DeviceCredentials, Tenant
from main.serializers.device_credentials import DeviceCredentialsSerializer
from main.serializers.device_profile import SimpleDeviceProfileSerializer
from main.utils.has_roomio_node import has_roomio_node


class SimpleDeviceSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["device_profile"] = str(instance.device_profile_id)
        data["tenant"] = str(instance.tenant_id)
        data["room"] = str(instance.room_id)
        return data

    class Meta:
        model = Device
        fields = (
            "id",
            "created_at",
            "name",
            "status",
            "type",
            "tenant",
            "room",
            "device_profile",
            "label",
            "additional_info",
            "device_data",
            "external_id",
        )


class DeviceSerializer(serializers.ModelSerializer):
    tenant = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all(), required=False)
    credentials = serializers.PrimaryKeyRelatedField(queryset=DeviceCredentials.objects.all(), required=False)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["credentials"] = (
            DeviceCredentialsSerializer(instance=instance.credentials).data
            if hasattr(instance, "credentials")
            else None
        )
        data["device_profile"] = SimpleDeviceProfileSerializer(instance.device_profile).data
        return data

    def create(self, validated_data):
        if validated_data.get("additional_info", {}).get("roomio_node") and has_roomio_node(
            validated_data.get("tenant_id")
        ):
            raise serializers.ValidationError({"detail": "You already have a device with a 'roomio_node'."})

        instance = super().create(validated_data)
        DeviceCredentials.objects.create(
            device=instance,
            credentials_id=get_random_letter(32),
            credentials_type="ACCESS_TOKEN",
        )
        return instance

    def update(self, instance, validated_data):
        if validated_data.get("additional_info", {}).get("roomio_node") and has_roomio_node(
            validated_data.get("tenant_id"), instance.id
        ):
            raise serializers.ValidationError({"detail": "You already have a device with a 'roomio_node'."})

        return super().update(instance, validated_data)

    class Meta:
        model = Device
        fields = (
            "id",
            "created_at",
            "name",
            "status",
            "type",
            "tenant",
            "customer",
            "room",
            "device_profile",
            "label",
            "additional_info",
            "device_data",
            "external_id",
            "credentials",
        )


class DeviceFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("created_at", "-created_at", "name", "-name", "status", "-status")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("name", "device_profile__name"), required=False)
    search_value = serializers.CharField(required=False)
    status = serializers.BooleanField(allow_null=True, required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)

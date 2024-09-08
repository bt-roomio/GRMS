from rest_framework import serializers

from core.utils.random_letter import get_random_letter
from core.utils.serializers import ValidatorSerializer
from main.models import Device, Tenant, DeviceCredentials
from main.serializers.device_credentials import DeviceCredentialsSerializer


class SimpleDeviceSerializer(serializers.ModelSerializer):
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
        return data

    def create(self, validated_data):
        instance = super().create(validated_data)
        DeviceCredentials.objects.create(
            device=instance, credentials_id=get_random_letter(32), credentials_type="ACCESS_TOKEN"
        )
        return instance

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
    SORT_FIELDS = ("name", "-name", "status", "-status")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("name",), required=False)
    search_value = serializers.CharField(required=False)
    status = serializers.BooleanField(allow_null=True, required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)

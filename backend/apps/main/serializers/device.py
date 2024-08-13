from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Device, Tenant


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


class DeviceFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("name", "-name", "status", "-status")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search = serializers.CharField(max_length=255, required=False)
    status = serializers.BooleanField(allow_null=True, required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)

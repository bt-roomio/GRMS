from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import DeviceProfile


class SimpleDeviceProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceProfile
        fields = (
            "id",
            "name",
            "tenant",
        )


class DeviceProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceProfile
        fields = (
            "id",
            "created_at",
            "name",
            "type",
            "state",
            "tenant",
            "active",
            "image",
            "transport_type",
            "provision_type",
            "profile_data",
            "description",
            "is_default",
            "default_queue_name",
            "provision_device_key",
            "external_id",
        )
        read_only_fields = ("active",)


class DeviceProfileFilterParams(ValidatorSerializer):
    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    state = serializers.BooleanField(allow_null=True)
    search_field = serializers.ChoiceField(choices=("name", "type"), required=False)
    search_value = serializers.CharField(required=False)


class DeviceProfileQuickFilterParams(DeviceProfileFilterParams):
    page = None
    size = None
    state = None
    search_field = None

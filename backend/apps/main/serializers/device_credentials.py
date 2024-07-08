from main.models import Device
from rest_framework import serializers


class DeviceSimpleCredentialsSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["isGateway"] = instance.additional_info and instance.additional_info.get("gateway") or False
        return data

    class Meta:
        model = Device
        fields = ("id",)


class DeviceCredentialsSerializer(serializers.Serializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["device"] = DeviceSimpleCredentialsSerializer(instance.device).data
        return data

from rest_framework import serializers

from main.models import Device, DeviceCredentials


class DeviceSimpleCredentialsSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["isGateway"] = instance.additional_info and instance.additional_info.get("gateway") or False
        return data

    class Meta:
        model = Device
        fields = ("id",)


class DeviceCredentialsDetailSerializer(serializers.Serializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["device"] = DeviceSimpleCredentialsSerializer(instance.device).data
        return data


class DeviceCredentialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceCredentials
        fields = ("id", "credentials_id", "credentials_type", "credentials_value")

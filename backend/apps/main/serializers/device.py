from rest_framework import serializers

from main.models import Device
from main.serializers.attribute_kv import AttributeKvSimpleSerializer


class DeviceSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["attributes"] = AttributeKvSimpleSerializer(instance.attribute_kvs, many=True).data
        return data

    class Meta:
        model = Device
        fields = (
            "id",
            "created_at",
            "name",
            "type",
            "status",
            "tenant",
            "customer",
            "room",
            "device_profile",
            "label",
            "additional_info",
            "device_data",
            "external_id",
        )

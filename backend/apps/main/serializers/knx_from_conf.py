from rest_framework import serializers

from main.services.device_config import (
    DEFAULT_PROFILE_NAME,
    CanonicalDevice,
    create_devices_from_config,
    require_active_gateway,
)
from shuttle.utils.camel_to_snake import to_snake_case_data


class KnxTagSerializer(serializers.Serializer):
    key = serializers.CharField()

    class Meta:
        ref_name = "KnxDeviceConfigTag"


class KnxDeviceInfoSerializer(serializers.Serializer):
    device_name_expression = serializers.CharField()
    device_profile_name_expression = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        ref_name = "KnxDeviceInfo"


class KnxDeviceSerializer(serializers.Serializer):
    device_info = KnxDeviceInfoSerializer()
    timeseries = KnxTagSerializer(many=True, required=False)
    attributes = KnxTagSerializer(many=True, required=False)
    attribute_updates = KnxTagSerializer(many=True, required=False)

    class Meta:
        ref_name = "KnxDevice"


class KnxClientSerializer(serializers.Serializer):
    devices = KnxDeviceSerializer(many=True)

    class Meta:
        ref_name = "KnxClient"


def knx_to_canonical(clients) -> list[CanonicalDevice]:
    """Adapter: flatten KNX clients[].devices[] (denormalized) -> canonical."""
    canonical = []
    for client in clients:
        for dev in client.get("devices", []):
            info = dev["device_info"]
            canonical.append(
                CanonicalDevice(
                    name=info["device_name_expression"],
                    profile_name=info.get("device_profile_name_expression") or DEFAULT_PROFILE_NAME,
                    timeseries=[t["key"] for t in dev.get("timeseries", [])],
                    attributes=[t["key"] for t in dev.get("attributes", [])],
                    attribute_updates=[t["key"] for t in dev.get("attribute_updates", [])],
                )
            )
    return canonical


class KnxDeviceFromConfSerializer(serializers.Serializer):
    gateway_id = serializers.UUIDField(required=True)
    clients = KnxClientSerializer(many=True)

    def validate(self, attrs):
        attrs["gateway_obj"] = require_active_gateway(self.context["tenant"], attrs.get("gateway_id"))
        if not any(client.get("devices") for client in attrs.get("clients", [])):
            raise serializers.ValidationError({"detail": "No devices found"})
        return attrs

    def to_internal_value(self, data):
        return super().to_internal_value(to_snake_case_data(data))

    def to_representation(self, instance):
        # `instance` is the summary returned by create(); echo it as-is rather
        # than reflecting it back through the (large) declared input fields.
        return instance

    def create(self, validated_data):
        tenant = self.context["tenant"]
        gateway = validated_data.pop("gateway_obj")  # from validate()
        gateway_id = validated_data.pop("gateway_id")
        clients = validated_data.pop("clients")

        summary = create_devices_from_config(
            tenant=tenant,
            gateway=gateway,
            devices=knx_to_canonical(clients),
        )

        return {
            "gateway_id": gateway_id,
            "devices": summary["device_names"],
            "devices_created": summary["devices_created"],
            "ts_latest_created": summary["ts_latest_created"],
            "attributes_created": summary["attributes_created"],
            "relations_created": summary["relations_created"],
        }

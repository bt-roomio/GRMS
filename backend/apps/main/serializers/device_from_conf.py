from rest_framework import serializers

from main.services.device_config import (
    DEFAULT_PROFILE_NAME,
    CanonicalDevice,
    create_devices_from_config,
    require_active_gateway,
)
from shuttle.utils.camel_to_snake import to_snake_case_data


class DeviceMacAddressSerializer(serializers.Serializer):
    mac_address = serializers.CharField()
    address_map_id = serializers.IntegerField()


class TagSerializer(serializers.Serializer):
    tag = serializers.CharField()

    class Meta:
        ref_name = "DeviceConfigTag"


class AddressMapsSerializer(serializers.Serializer):
    timeseries = TagSerializer(many=True, required=False)
    attributes = TagSerializer(many=True, required=False)
    attribute_updates = TagSerializer(many=True, required=False)
    address_map_id = serializers.IntegerField()


def roomio_to_canonical(devices_in, maps_in) -> list[CanonicalDevice]:
    """Adapter: join Roomio devices to their shared address maps -> canonical."""
    maps_by_id = {m["address_map_id"]: m for m in maps_in}
    canonical = []
    for dev_in in devices_in:
        amap = maps_by_id.get(dev_in["address_map_id"])
        if not amap:
            continue
        canonical.append(
            CanonicalDevice(
                name=dev_in["mac_address"],
                profile_name=DEFAULT_PROFILE_NAME,
                timeseries=[t["tag"] for t in amap.get("timeseries", [])],
                attributes=[t["tag"] for t in amap.get("attributes", [])],
                attribute_updates=[t["tag"] for t in amap.get("attribute_updates", [])],
            )
        )
    return canonical


class DeviceFromConfSerializer(serializers.Serializer):
    gateway_id = serializers.UUIDField(required=True)
    devices = DeviceMacAddressSerializer(many=True)
    address_maps = AddressMapsSerializer(many=True)

    def validate(self, attrs):
        attrs["gateway_obj"] = require_active_gateway(self.context["tenant"], attrs.get("gateway_id"))
        return attrs

    def to_internal_value(self, data):
        devices = [i for i in data.get("devices", []) if "macAddress" in i and "addressMapId" in i]
        if not devices:
            raise serializers.ValidationError({"detail": "No devices found"})
        data["devices"] = devices
        return super().to_internal_value(to_snake_case_data(data))

    def create(self, validated_data):
        tenant = self.context["tenant"]
        gateway = validated_data.pop("gateway_obj")  # from validate()
        gateway_id = validated_data.pop("gateway_id")
        devices_in = validated_data.pop("devices")
        maps_in = validated_data.pop("address_maps")

        create_devices_from_config(
            tenant=tenant,
            gateway=gateway,
            devices=roomio_to_canonical(devices_in, maps_in),
        )

        # Echo the original request shape back to the caller (unchanged contract).
        result_devices = [{"mac_address": d["mac_address"], "address_map_id": d["address_map_id"]} for d in devices_in]
        return {
            "gateway_id": gateway_id,
            "devices": result_devices,
            "address_maps": maps_in,
        }

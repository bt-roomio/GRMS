from django.db import transaction

from rest_framework import serializers

from main.services.device_config import (
    DEFAULT_PROFILE_NAME,
    CanonicalDevice,
    RoomSpec,
    create_devices_from_config,
    link_devices_to_rooms,
    require_active_gateway,
)
from shuttle.utils.camel_to_snake import to_snake_case_data


class DeviceMacAddressSerializer(serializers.Serializer):
    mac_address = serializers.CharField()
    address_map_id = serializers.IntegerField()
    room_number = serializers.CharField(required=False)
    room_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    floor = serializers.CharField(required=False, allow_blank=True)
    block = serializers.CharField(required=False, allow_blank=True)


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
        data = to_snake_case_data(data)
        devices = [i for i in data.get("devices", []) if "mac_address" in i and "address_map_id" in i]
        if not devices:
            raise serializers.ValidationError({"detail": "No devices found"})
        data["devices"] = devices
        return super().to_internal_value(data)

    def create(self, validated_data):
        tenant = self.context["tenant"]
        gateway = validated_data.pop("gateway_obj")  # from validate()
        gateway_id = validated_data.pop("gateway_id")
        devices_in = validated_data.pop("devices")
        maps_in = validated_data.pop("address_maps")

        device_rooms = {}
        for d in devices_in:
            if d.get("room_number"):
                spec = RoomSpec(d["room_number"], d.get("room_type"), d.get("floor"), d.get("block"))
                device_rooms.setdefault(d["mac_address"], spec)

        with transaction.atomic():
            create_devices_from_config(
                tenant=tenant,
                gateway=gateway,
                devices=roomio_to_canonical(devices_in, maps_in),
            )
            linked_rooms = link_devices_to_rooms(tenant=tenant, device_rooms=device_rooms) if device_rooms else {}

        # Echo the request shape back, plus the room each device was linked to.
        result_devices = []
        for d in devices_in:
            result = {"mac_address": d["mac_address"], "address_map_id": d["address_map_id"]}
            if room := linked_rooms.get(d["mac_address"]):
                result.update(
                    room_number=room.number,
                    floor=room.floor,
                    block=room.block,
                    room_type=room.type.title if room.type else None,
                )
            result_devices.append(result)
        return {
            "gateway_id": gateway_id,
            "devices": result_devices,
            "address_maps": maps_in,
        }

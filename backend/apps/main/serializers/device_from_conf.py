from rest_framework import serializers

from main.models import Device, DeviceProfile
from shuttle.models import AttributeKv, TsKvDictionary, TsKvLatest
from shuttle.utils.camel_to_snake import to_snake_case_data


class DeviceMacAddressSerializer(serializers.Serializer):
    mac_address = serializers.CharField()
    address_map_id = serializers.IntegerField()


class TagSerializer(serializers.Serializer):
    tag = serializers.CharField()


class AddressMapsSerializer(serializers.Serializer):
    timeseries = TagSerializer(many=True, required=False)
    attributes = TagSerializer(many=True, required=False)
    attribute_updates = TagSerializer(many=True, required=False)
    address_map_id = serializers.IntegerField()


class DeviceFromConfSerializer(serializers.Serializer):
    devices = DeviceMacAddressSerializer(many=True)
    address_maps = AddressMapsSerializer(many=True)

    def to_internal_value(self, data):
        devices = [i for i in data.get("devices", []) if "macAddress" and "addressMapId" in i]
        data["devices"] = devices
        if not devices:
            raise serializers.ValidationError({"detail": "No devices found"})

        return super().to_internal_value(to_snake_case_data(data))

    def create(self, validated_data):
        result = {
            "devices": [],
            "address_maps": [],
        }
        tenant = self.context.get("tenant")
        devices = validated_data.pop("devices")
        address_maps = validated_data.pop("address_maps")
        result["devices"] = devices
        result["address_maps"] = address_maps

        device_profile = DeviceProfile.objects.filter(tenant=tenant, name__iexact="Default").first()
        if not device_profile:
            raise serializers.ValidationError({"detail": "First create device profile!"})

        for device in devices:
            device_obj, _ = Device.objects.get_or_create(
                name=device.get("mac_address"),
                tenant=tenant,
                is_active=True,
                defaults={"device_profile": device_profile, "type": "default"},
            )
            for address_map in address_maps:
                for tag in address_map.get("timeseries"):
                    dict_ts_kv_key_id, _ = TsKvDictionary.objects.get_or_create(key=tag.get("tag"))
                    TsKvLatest.objects.get_or_create(
                        entity_id=device_obj.id, key=dict_ts_kv_key_id, defaults={"long_v": 0}
                    )
                for tag in address_map.get("attribute_updates"):
                    AttributeKv.objects.get_or_create(
                        entity_type="DEVICE",
                        attribute_type="SHARED_SCOPE",
                        attribute_key=tag.get("tag"),
                        entity_id=device_obj.id,
                        defaults={"long_v": 0},
                    )
                for tag in address_map.get("attributes"):
                    AttributeKv.objects.get_or_create(
                        entity_type="DEVICE",
                        attribute_type="CLIENT_SCOPE",
                        attribute_key=tag.get("tag"),
                        entity_id=device_obj.id,
                        defaults={"long_v": 0},
                    )
        return result

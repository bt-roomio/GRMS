from rest_framework import serializers

from core.serializers.camelcase import CamelCaseMixin
from core.utils.serializers import ValidatorSerializer
from main.models import DeviceProfile, Device
from shuttle.models import TsKvDictionary, TsKvLatest, AttributeKv


class DeviceMacAddressSerializer(serializers.Serializer):
    mac_address = serializers.CharField()
    address_map_id = serializers.IntegerField()


class TimeseriesSerializer(serializers.Serializer):
    tag = serializers.CharField()
    address = serializers.IntegerField()


class AttributesSerializer(serializers.Serializer):
    tag = serializers.CharField()
    address = serializers.IntegerField()


class DeviceFromConfSerializer(CamelCaseMixin, serializers.Serializer):
    devices = DeviceMacAddressSerializer(many=True)
    timeseries = TimeseriesSerializer(many=True, required=False)
    attribute_updates = AttributesSerializer(many=True, required=False)
    attributes = AttributesSerializer(many=True, required=False)

    def create(self, validated_data):
        print(validated_data)
        tenant = self.context.get("tenant")
        devices = validated_data.pop("devices")
        timeseries = validated_data.pop("timeseries")
        attribute_updates = validated_data.pop("attribute_updates")
        attributes = validated_data.pop("attributes")

        device_profile = DeviceProfile.objects.filter(tenant=tenant, name="default").first()
        if not device_profile:
            raise serializers.ValidationError({"detail": "First create device profile!"})

        result = {"devices": []}
        for device in devices:
            device_obj, _ = Device.objects.get_or_create(
                name=device.get("mac_address"),
                tenant=tenant,
                defaults={"device_profile": device_profile, "type": "default"},
            )
            if timeseries:
                tags = [i for i in timeseries if device.get("address_map_id") == i.get("address")]
                for tag in tags:
                    dict_ts_kv_key_id = TsKvDictionary.objects.get_key_id(key=tag.get("tag"))
                    TsKvLatest.objects.get_or_create(
                        entity_id=device_obj.id, key=dict_ts_kv_key_id, defaults={"long_v": 0}
                    )

            if attribute_updates:
                tags = [i for i in attribute_updates if device.get("address_map_id") == i.get("address")]
                for tag in tags:
                    AttributeKv.objects.get_or_create(
                        entity_type="DEVICE",
                        attribute_type="SHARED_SCOPE",
                        attribute_key=tag.get("tag"),
                        entity_id=device_obj.id,
                        defaults={"long_v": 0},
                    )
            if attributes:
                tags = [i for i in attributes if device.get("address_map_id") == i.get("address")]
                for tag in tags:
                    AttributeKv.objects.get_or_create(
                        entity_type="DEVICE",
                        attribute_type="CLIENT_SCOPE",
                        attribute_key=tag.get("tag"),
                        entity_id=device_obj.id,
                        defaults={"long_v": 0},
                    )
        return result


class DeviceFromConfFilterParams(ValidatorSerializer):
    devices = serializers.ListField(child=serializers.CharField())

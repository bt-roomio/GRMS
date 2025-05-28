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
        devices = [i for i in data.get("devices", []) if "macAddress" in i and "addressMapId" in i]
        if not devices:
            raise serializers.ValidationError({"detail": "No devices found"})
        data["devices"] = devices
        return super().to_internal_value(to_snake_case_data(data))

    def create(self, validated_data):
        tenant = self.context["tenant"]
        devices_in = validated_data.pop("devices")
        maps_in = validated_data.pop("address_maps")

        # 1) Default profile
        profile, _ = DeviceProfile.objects.get_or_create(tenant=tenant, name__iexact="Default")

        # 2) Index address_maps by ID
        maps_by_id = {m["address_map_id"]: m for m in maps_in}

        # 3) Deduplicate MAC addresses
        macs = [d["mac_address"] for d in devices_in]
        unique_macs = list(dict.fromkeys(macs))

        # # 4) Bulk-create any new Devices
        existing = Device.objects.filter(tenant=tenant, name__in=unique_macs, is_active=True)
        to_create = []
        existing_names = {d.name for d in existing}
        for mac in unique_macs:
            if mac not in existing_names:
                to_create.append(
                    Device(
                        name=mac,
                        tenant=tenant,
                        is_active=True,
                        device_profile=profile,
                        type="default",
                    )
                )

        if to_create:
            Device.objects.bulk_create(to_create, ignore_conflicts=True)

        # **Always** re-fetch all Devices so dev_map is complete
        all_devs = Device.objects.filter(tenant=tenant, name__in=unique_macs, is_active=True)
        dev_map = {d.name: d for d in all_devs}

        # # 5) Gather all unique TS keys across all maps
        all_ts_tags = {tag["tag"] for m in maps_in for tag in m.get("timeseries", [])}
        # # 6) Bulk-upsert TsKvDictionary
        existing_dicts = TsKvDictionary.objects.filter(key__in=all_ts_tags)
        dict_map = {d.key: d for d in existing_dicts}
        missing = all_ts_tags - dict_map.keys()
        if missing:
            TsKvDictionary.objects.bulk_create([TsKvDictionary(key=tag) for tag in missing], ignore_conflicts=True)
            for d in TsKvDictionary.objects.filter(key__in=missing):
                dict_map[d.key] = d

        # # 7) Build deduped list of TsKvLatest
        latest_objs = []
        for dev_in in devices_in:
            dev = dev_map[dev_in["mac_address"]]
            amap = maps_by_id.get(dev_in["address_map_id"])
            if not amap:
                continue
            seen = set()
            for tag in amap.get("timeseries", []):
                ts_obj = dict_map[tag["tag"]]
                key = (dev.id, ts_obj.key_id)
                if key in seen:
                    continue
                seen.add(key)
                latest_objs.append(
                    TsKvLatest(
                        entity_id=dev.id,
                        key=ts_obj,
                        long_v=0,
                    )
                )

        if latest_objs:
            TsKvLatest.objects.bulk_create(
                latest_objs,
                update_conflicts=True,
                unique_fields=["entity_id", "key_id"],
                update_fields=["ts", "bool_v", "str_v", "long_v", "dbl_v", "json_v"],
            )

        # # 8) Build deduped list of AttributeKv
        attr_objs = []
        seen_attrs = set()
        for dev_in in devices_in:
            dev = dev_map[dev_in["mac_address"]]
            amap = maps_by_id.get(dev_in["address_map_id"])
            if not amap:
                continue
            for tag in amap.get("attribute_updates", []):
                key = ("DEVICE", "SHARED_SCOPE", dev.id, tag["tag"])
                if key not in seen_attrs:
                    seen_attrs.add(key)
                    attr_objs.append(
                        AttributeKv(
                            entity_type="DEVICE",
                            attribute_type="SHARED_SCOPE",
                            attribute_key=tag["tag"],
                            entity_id=dev.id,
                            long_v=0,
                        )
                    )
            for tag in amap.get("attributes", []):
                key = ("DEVICE", "CLIENT_SCOPE", dev.id, tag["tag"])
                if key not in seen_attrs:
                    seen_attrs.add(key)
                    attr_objs.append(
                        AttributeKv(
                            entity_type="DEVICE",
                            attribute_type="CLIENT_SCOPE",
                            attribute_key=tag["tag"],
                            entity_id=dev.id,
                            long_v=0,
                        )
                    )

        if attr_objs:
            AttributeKv.objects.bulk_create(
                attr_objs,
                update_conflicts=True,
                unique_fields=["entity_type", "attribute_type", "entity_id", "attribute_key"],
                update_fields=["long_v"],
            )

        result_devices = []
        for dev_in in devices_in:
            mac = dev_in["mac_address"]
            amap_id = dev_in["address_map_id"]
            result_devices.append(
                {
                    "mac_address": mac,
                    "address_map_id": amap_id,
                }
            )

        # 10) Возвращаем именно те поля, что описаны в сериализаторе
        return {
            "devices": result_devices,
            "address_maps": maps_in,  # здесь отдаём оригинальные данные address_maps
        }

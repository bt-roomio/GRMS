from rest_framework import serializers

from main.models import Device, DeviceProfile
from shuttle.models import AttributeKv, Relation, TsKvDictionary, TsKvLatest
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


class DeviceFromConfSerializer(serializers.Serializer):
    gateway_id = serializers.UUIDField(required=True)
    devices = DeviceMacAddressSerializer(many=True)
    address_maps = AddressMapsSerializer(many=True)

    def validate(self, attrs):
        tenant = self.context["tenant"]
        gateway_id = attrs.get("gateway_id")
        gateway = Device.objects.filter(
            id=gateway_id,
            tenant=tenant,
            is_active=True,
            additional_info__gateway=True,
        ).first()

        if not gateway:
            raise serializers.ValidationError(
                {"gateway_id": "Gateway not found or not an active gateway for this tenant."}
            )

        attrs["gateway_obj"] = gateway
        return attrs

    def to_internal_value(self, data):
        devices = [i for i in data.get("devices", []) if "macAddress" in i and "addressMapId" in i]
        if not devices:
            raise serializers.ValidationError({"detail": "No devices found"})
        data["devices"] = devices
        return super().to_internal_value(to_snake_case_data(data))

    def create(self, validated_data):
        tenant = self.context["tenant"]

        gateway: Device = validated_data.pop("gateway_obj")  # from validate()
        gateway_id = validated_data.pop("gateway_id")
        devices_in = validated_data.pop("devices")
        maps_in = validated_data.pop("address_maps")

        # 1) Default profile
        profile, _ = DeviceProfile.objects.get_or_create(tenant=tenant, name__iexact="Default")

        # 2) Index address_maps by ID
        maps_by_id = {m["address_map_id"]: m for m in maps_in}

        # 3) Deduplicate MAC addresses
        macs = [d["mac_address"] for d in devices_in]
        unique_macs = list(dict.fromkeys(macs))

        # 4) Bulk-create any new Devices
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
            existing_ts = set(
                TsKvLatest.objects.filter(
                    entity_id__in={obj.entity_id for obj in latest_objs},
                ).values_list("entity_id", "key_id")
            )
            latest_objs = [obj for obj in latest_objs if (obj.entity_id, obj.key.key_id) not in existing_ts]
            if latest_objs:
                TsKvLatest.objects.bulk_create(latest_objs, ignore_conflicts=True)

        # 8) Build deduped list of AttributeKv
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
            existing_attrs = set(
                AttributeKv.objects.filter(
                    entity_type="DEVICE",
                    entity_id__in={obj.entity_id for obj in attr_objs},
                ).values_list("entity_type", "attribute_type", "entity_id", "attribute_key")
            )
            attr_objs = [
                obj
                for obj in attr_objs
                if (obj.entity_type, obj.attribute_type, obj.entity_id, obj.attribute_key) not in existing_attrs
            ]
            if attr_objs:
                AttributeKv.objects.bulk_create(attr_objs, ignore_conflicts=True)

        # 9) Create Relations
        relation_objs = []
        for dev_in in devices_in:
            dev = dev_map[dev_in["mac_address"]]
            if dev.id == gateway.id:
                continue
            relation_objs.append(
                Relation(
                    from_id=gateway,
                    from_type="DEVICE",
                    relation_type_group="COMMON",
                    relation_type="Created",
                    to_id=dev,
                    to_type="DEVICE",
                )
            )
        if relation_objs:
            Relation.objects.bulk_create(relation_objs, ignore_conflicts=True)

        # 10) Build response payload (include gateway_id back)
        result_devices = [{"mac_address": d["mac_address"], "address_map_id": d["address_map_id"]} for d in devices_in]
        return {
            "gateway_id": gateway_id,
            "devices": result_devices,
            "address_maps": maps_in,
        }

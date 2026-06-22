from rest_framework import serializers

from core.serializers.dynamic import DynamicField
from core.utils.serializers import ValidatorSerializer
from main.models import Device
from main.serializers.device import SimpleDeviceSerializer
from shuttle.models import AttributeKv
from shuttle.utils.get_non_null_field import get_non_null_column, get_non_null_field


class SimpleAttributeSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["entity"] = str(instance.entity_id)
        return data

    class Meta:
        model = AttributeKv
        fields = (
            "id",
            "entity_type",
            "entity",
            "attribute_type",
            "attribute_key",
            "bool_v",
            "str_v",
            "long_v",
            "dbl_v",
            "json_v",
            "last_update_ts",
        )


class AttributesChangeSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["ATTRIBUTES", "TELEMETRY"])
    scope = serializers.ChoiceField(choices=AttributeKv.ENTITY_TYPE, allow_null=True, required=False)
    items = serializers.DictField()


class AttributeKvPath(serializers.Serializer):
    device_id = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all())
    scope = serializers.ChoiceField(choices=[AttributeKv.SHARED_SCOPE, AttributeKv.SERVER_SCOPE])


class AttributesChangeFilterPath(ValidatorSerializer):
    entity_type = serializers.ChoiceField(choices=["Room", "RoomType", "AllRoomType"])
    entity_id = serializers.UUIDField(required=False)


class AttributeSerializer(serializers.Serializer):
    last_update_ts = serializers.IntegerField()
    key_name = serializers.CharField()
    value = DynamicField()


class RoomAttributeSerializer(serializers.Serializer):
    """Shapes a ``get_attributes_by_room`` ``.values()`` row: renames the entity/key
    columns and picks the first non-null typed value, preserving its native type."""

    id = serializers.UUIDField()
    key_name = serializers.CharField(source="attribute_key")
    last_update_ts = serializers.IntegerField()
    value = serializers.SerializerMethodField()

    def get_value(self, obj):
        return get_non_null_column(obj)[1]


class AttributeFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("last_update_ts", "-last_update_ts", "key_name", "-key_name")

    page = serializers.IntegerField(default=1, min_value=1)
    size = serializers.IntegerField(default=25, max_value=500)
    sort_by = serializers.ListField(child=serializers.CharField(), required=False)
    scope = serializers.ChoiceField(
        choices=[AttributeKv.SHARED_SCOPE, AttributeKv.SERVER_SCOPE, AttributeKv.CLIENT_SCOPE]
    )
    device = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all())


class InactiveAttributesFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("last_update_ts", "-last_update_ts")
    page = serializers.IntegerField(default=1, min_value=1)
    size = serializers.IntegerField(default=25, max_value=500)
    sort_by = serializers.ChoiceField(choices=SORT_FIELDS, default="-last_update_ts")


class InactiveDeviceAttributeSerializer(serializers.ModelSerializer):
    device = serializers.SerializerMethodField()
    ip_address = serializers.SerializerMethodField()

    class Meta:
        model = AttributeKv
        fields = ("last_update_ts", "ip_address", "device")

    def get_device(self, obj):
        return SimpleDeviceSerializer(
            obj.entity,
            context={**self.context, "exclude_room_obj": False},  # force include room_obj
        ).data

    def get_ip_address(self, obj):
        attrs = getattr(getattr(obj, "entity", None), "prefetched_ip_attrs", None) or []
        if not attrs:
            return None
        latest = attrs[0]
        _field, value = get_non_null_field(latest)
        return value

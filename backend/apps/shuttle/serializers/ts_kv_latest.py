from rest_framework import serializers

from core.serializers.dynamic import DynamicField
from core.utils.serializers import ValidatorSerializer
from main.models import Device
from shuttle.models import TsKvLatest
from shuttle.utils.get_non_null_field import get_non_null_column


class SimpleTsKvLatestSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["entity"] = str(instance.entity_id)
        data["key"] = instance.key.key
        return data

    class Meta:
        model = TsKvLatest
        fields = ("id", "ts", "entity", "key", "bool_v", "str_v", "long_v", "dbl_v", "json_v")


class TsKvLatestSerializer(serializers.Serializer):
    ts = serializers.IntegerField()
    key_name = serializers.CharField()
    value = DynamicField()


class RoomTsKvLatestSerializer(serializers.Serializer):
    """Shapes a ``get_ts_kv_latest_by_room`` ``.values()`` row: renames the entity/key
    columns and picks the first non-null typed value, preserving its native type."""

    id = serializers.UUIDField()
    key_name = serializers.CharField(source="key__key")
    ts = serializers.IntegerField()
    value = serializers.SerializerMethodField()

    def get_value(self, obj):
        return get_non_null_column(obj)[1]


class TsKvLatestIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TsKvLatest
        fields = ("id", "ts", "entity_id", "key", "bool_v", "str_v", "long_v", "dbl_v")


class TsKvLatestFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("ts", "-ts", "key_name", "-key_name")
    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=15)
    device = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all())
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)


class TsKvLatestIntegrationFilterParams(ValidatorSerializer):
    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=15)
    keys = serializers.ListField(child=serializers.CharField())

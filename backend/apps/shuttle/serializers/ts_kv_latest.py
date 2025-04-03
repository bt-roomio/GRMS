from rest_framework import serializers

from core.serializers.dynamic import DynamicField
from core.utils.serializers import ValidatorSerializer
from main.models import Device
from shuttle.models import TsKvLatest


class TsKvLatestSerializer(serializers.Serializer):
    ts = serializers.IntegerField()
    key_name = serializers.CharField()
    value = DynamicField()


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

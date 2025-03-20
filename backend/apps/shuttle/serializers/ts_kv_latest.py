from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from shuttle.models import TsKvLatest


class TsKvLatestSerializer(serializers.ModelSerializer):
    class Meta:
        model = TsKvLatest
        fields = ("id", "ts", "entity_id", "key", "bool_v", "str_v", "long_v", "dbl_v")


class TsKvLatestFilterParams(ValidatorSerializer):
    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=15)
    keys = serializers.ListField(child=serializers.CharField())

from rest_framework import serializers

from shuttle.models import TsKvLatest


class TsKvLatestSerializer(serializers.ModelSerializer):
    class Meta:
        model = TsKvLatest
        fields = (
            "id",
            "entity",
            "key",
            "bool_v",
            "str_v",
            "long_v",
            "dbl_v",
            "json_v",
            "tenant",
        )

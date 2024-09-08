from rest_framework import serializers

from shuttle.models import TsKv


class TsKvSerializer(serializers.ModelSerializer):
    class Meta:
        model = TsKv
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

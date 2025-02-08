from rest_framework import serializers

from shuttle.models import AttributeKv


class AttributeKvSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeKv
        fields = (
            "attribute_key",
            "str_v",
        )

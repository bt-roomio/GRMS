from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from shuttle.models import Relation


class RelationSerializer(serializers.ModelSerializer):
    def update(self, instance, validated_data):
        validated_data.pop("from_id", None)
        validated_data.pop("from_type", None)
        validated_data.pop("to_id", None)
        validated_data.pop("to_type", None)
        validated_data.pop("relation_type_group", None)
        validated_data.pop("relation_type", None)
        return super().update(instance, validated_data)

    class Meta:
        model = Relation
        fields = (
            "id",
            "from_id",
            "from_type",
            "to_id",
            "to_type",
            "relation_type_group",
            "relation_type",
            "additional_info",
        )


class RelationFilterParams(ValidatorSerializer):
    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)

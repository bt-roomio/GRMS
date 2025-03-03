from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Device
from shuttle.models import Relation


class SimpleDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ("id", "name")


class RelationSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["to_id"] = SimpleDeviceSerializer(instance.to_id).data
        data["from_id"] = SimpleDeviceSerializer(instance.from_id).data
        return data

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
    from_id = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all(), required=False)
    to_id = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all(), required=False)

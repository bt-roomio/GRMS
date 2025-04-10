from rest_framework import serializers

from core.serializers.dynamic import DynamicField
from core.utils.serializers import ValidatorSerializer
from main.models import Device
from shuttle.models import AttributeKv


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


class AttributeFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("last_update_ts", "-last_update_ts", "key_name", "-key_name")

    page = serializers.IntegerField(default=1, min_value=1)
    size = serializers.IntegerField(default=25, max_value=500)
    sort_by = serializers.ListField(child=serializers.CharField(), required=False)
    scope = serializers.ChoiceField(
        choices=[AttributeKv.SHARED_SCOPE, AttributeKv.SERVER_SCOPE, AttributeKv.CLIENT_SCOPE]
    )
    device = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all())

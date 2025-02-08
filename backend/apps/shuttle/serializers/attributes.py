from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Device
from shuttle.models import AttributeKv


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

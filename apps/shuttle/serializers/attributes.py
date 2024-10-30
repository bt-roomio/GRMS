from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Device
from shuttle.models import AttributeKv


class AttributesChangeSerializer(serializers.ModelSerializer):
    fields_to_be_removed = ["str_v", "bool_v", "long_v", "dbl_v", "json_v"]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        for field in self.fields_to_be_removed:
            try:
                if rep[field] is None:
                    rep.pop(field)
            except KeyError:
                pass
        return rep

    class Meta:
        model = AttributeKv
        fields = ("id", "attribute_key", "str_v", "bool_v", "long_v", "dbl_v", "json_v")


class AttributeKvParams(serializers.Serializer):
    deviceId = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all())
    scope = serializers.ChoiceField(choices=[AttributeKv.SHARED_SCOPE, AttributeKv.SERVER_SCOPE])


class AttributesChangeFilterPath(ValidatorSerializer):
    entity_type = serializers.ChoiceField(choices=["Room", "RoomType", "Tenant"])
    entity_id = serializers.UUIDField()

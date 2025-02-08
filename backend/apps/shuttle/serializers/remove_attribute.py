from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Device
from shuttle.models import AttributeKv


class RemoveAttributeFilterParams(ValidatorSerializer):
    keys = serializers.ListField(child=serializers.CharField())


class RemoveAttributeFilterPath(ValidatorSerializer):
    device_id = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all())
    scope = serializers.ChoiceField(choices=AttributeKv.ENTITY_TYPE)

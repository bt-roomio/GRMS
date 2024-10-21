from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Device


class ControllerFilterPath(ValidatorSerializer):
    device_id = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all())
    name = serializers.CharField()

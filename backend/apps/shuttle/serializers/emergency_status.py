from core.utils.serializers import ValidatorSerializer
from rest_framework import serializers


class EmergencyStatusFilterParams(ValidatorSerializer):
    delisting_devices = serializers.ListField(child=serializers.CharField(), required=False)
    keys = serializers.ListField(child=serializers.CharField())
    room_types = serializers.ListField(child=serializers.CharField(), required=False)

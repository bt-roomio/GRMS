from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer


class RunCommandSerializer(ValidatorSerializer):
    command = serializers.CharField(max_length=4096)
    timeout = serializers.FloatField(required=False, min_value=1, max_value=600)

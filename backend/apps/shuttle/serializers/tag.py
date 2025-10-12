from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Device
from shuttle.models import AttributeKv


class TagFilterPath(ValidatorSerializer):
    device_id = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all())
    scope = serializers.ChoiceField(
        choices=[
            AttributeKv.SHARED_SCOPE,
            AttributeKv.SERVER_SCOPE,
            AttributeKv.CLIENT_SCOPE,
            "LATEST_TELEMETRY",
        ]
    )


class TagFilterParams(ValidatorSerializer):
    tags = serializers.ListField(child=serializers.CharField())

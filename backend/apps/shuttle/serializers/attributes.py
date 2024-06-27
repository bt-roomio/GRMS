from rest_framework import serializers

from shuttle.models import AttributeKv
from main.models import Device


class AttributeKvParams(serializers.Serializer):
    deviceId = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all())
    scope = serializers.ChoiceField(choices=[AttributeKv.SHARED_SCOPE, AttributeKv.SERVER_SCOPE])

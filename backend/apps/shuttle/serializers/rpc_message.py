from rest_framework import serializers

from shuttle.models import RPCMessage


class RPCMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RPCMessage
        fields = ("id", "created_at", "request_id", "sent", "additional_info")

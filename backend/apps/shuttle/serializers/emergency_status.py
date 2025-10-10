from core.utils.serializers import ValidatorSerializer
from rest_framework import serializers


class EmergencyStatusFilterParams(ValidatorSerializer):
    delisting_devices = serializers.ListField(child=serializers.CharField(), required=False)
    devices = serializers.ListField(child=serializers.CharField(), required=False)
    keys = serializers.ListField(child=serializers.CharField())
    room_types = serializers.ListField(child=serializers.CharField(), required=False)
    data_type = serializers.ChoiceField(choices=['telemetry', 'attribute'], required=True)
    attribute_scope = serializers.ChoiceField(
        choices=['CLIENT_SCOPE', 'SERVER_SCOPE', 'SHARED_SCOPE'],
        required=False,
        help_text="Required if data_type is 'attribute'"
    )


class TelemetryDataItemSerializer(serializers.Serializer):
    key_name = serializers.CharField()
    ts = serializers.IntegerField()
    value = serializers.JSONField(allow_null=True)


class RoomSerializer(serializers.Serializer):
    number = serializers.CharField(allow_null=True)
    id = serializers.CharField(allow_null=True)


class DeviceTelemetrySerializer(serializers.Serializer):
    device_id = serializers.CharField()
    room = RoomSerializer()
    telemetry_data = TelemetryDataItemSerializer(many=True, source='data')


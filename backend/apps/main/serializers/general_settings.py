import json

from rest_framework import serializers


class DoorLockSerializer(serializers.Serializer):
    ving_card = serializers.BooleanField(default=False)
    kaba = serializers.BooleanField(default=False)


class GeneralSettingsSerializer(serializers.Serializer):
    lang = serializers.CharField(max_length=255, default='en')
    timezone = serializers.IntegerField(default=0)
    controllers_sync = serializers.BooleanField(default=False)
    check_in_out = serializers.BooleanField(default=False)
    vip_status = serializers.BooleanField(default=False)
    suite_rooms_controls_sync = serializers.BooleanField(default=False)
    laundry = serializers.BooleanField(default=False)
    visionline = serializers.BooleanField(default=False)
    opera_integration = serializers.BooleanField(default=False)
    visionline_card_system = serializers.BooleanField(default=False)
    aperio_locks = serializers.BooleanField(default=False)
    door_lock = DoorLockSerializer(default=dict)
    auto_checkout = serializers.BooleanField(default=False)

    def update(self, instance, validated_data):
        instance.additional_info = json.dumps({'general_settings': validated_data})
        instance.save()
        return instance

    def to_representation(self, instance):
        return {'tenant_id': instance.id, **self.validated_data}

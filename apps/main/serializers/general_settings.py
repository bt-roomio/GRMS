from rest_framework import serializers


class DoorLockSerializer(serializers.Serializer):
    ving_card = serializers.BooleanField(default=False)
    kaba = serializers.BooleanField(default=False)


class GeneralSettingsSerializer(serializers.Serializer):
    lang = serializers.CharField(max_length=255, default="en")
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
    aggregate_db = serializers.BooleanField(default=False)

    def update(self, instance, validated_data):
        general_settings = instance.additional_info.get("general_settings", {}) if instance.additional_info else {}
        instance.additional_info = {"general_settings": {**general_settings, **validated_data}}
        instance.save()
        return instance

    def to_representation(self, instance):
        general_settings = instance.additional_info.get("general_settings", {}) if instance.additional_info else {}
        defaults = {
            field_name: (
                field.default
                if not isinstance(field, serializers.BaseSerializer)
                else field.to_representation(field.get_default())
            )
            for field_name, field in self.fields.items()
        }

        merged = {**defaults, **general_settings}
        return {"tenant_id": instance.id, **merged}

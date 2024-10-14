from rest_framework import serializers

from main.models import Dashboard


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
    main_dashboard = serializers.PrimaryKeyRelatedField(queryset=Dashboard.objects.all(), required=False, many=False)
    public_space_dashboard = serializers.PrimaryKeyRelatedField(
        queryset=Dashboard.objects.all(), required=False, many=False
    )

    def validate_main_dashboard(self, value):
        dashboard = Dashboard.objects.filter(title=value).first()
        if not dashboard:
            raise serializers.ValidationError({"main_dashboard": [f"Object with title={value} does not exist."]})
        return str(dashboard.id)

    def validate_public_space_dashboard(self, value):
        dashboard = Dashboard.objects.filter(title=value).first()
        if not dashboard:
            raise serializers.ValidationError({"main_dashboard": [f"Object with title={value} does not exist."]})
        return str(dashboard.id)

    def update(self, instance, validated_data):
        general_settings = instance.additional_info.get("general_settings", {}) if instance.additional_info else {}
        instance.additional_info = {"general_settings": {**general_settings, **validated_data}}
        instance.save()
        return instance

    def to_representation(self, instance):
        g_settings = instance.additional_info.get("general_settings", {}) if instance.additional_info else {}
        for field_name, field in self.fields.items():
            if field_name == "main_dashboard":
                g_settings[field_name] = g_settings.get(field_name, None)
            elif field_name == "public_space_dashboard":
                g_settings[field_name] = g_settings.get(field_name, None)
            elif field_name == "door_lock":
                g_settings[field_name] = g_settings.get(field_name, field.to_representation(field.get_default()))
            else:
                g_settings[field_name] = g_settings.get(field_name, field.default)

        merged = {**g_settings}
        return {"tenant_id": instance.id, **merged}

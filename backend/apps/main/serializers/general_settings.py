from datetime import time

from rest_framework import serializers

from main.models import Dashboard
from shuttle.models import AttributeKv


class DoorLockSerializer(serializers.Serializer):
    ving_card = serializers.BooleanField(default=False)
    kaba = serializers.BooleanField(default=False)


class TagSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    is_boolean = serializers.BooleanField(allow_null=True, required=False)
    tag_type = serializers.ChoiceField(
        choices=("attribute", "telemetry"),
        default="telemetry",
        error_messages={"invalid_choice": "Type of the tag, e.g., ['attribute', 'telemetry']"},
    )
    attribute_scope = serializers.ChoiceField(
        choices=AttributeKv.ENTITY_TYPE,
        default="",
        allow_blank=True,
        error_messages={"invalid_choice": f"Scope of the attribute, e.g., {[k[0] for k in AttributeKv.ENTITY_TYPE]}"},
    )
    config = serializers.JSONField(default={})

    class Meta:
        ref_name = "RoomFieldTag"

    def validate(self, attrs):
        if attrs["tag_type"] == "attribute" and not attrs.get("attribute_scope"):
            raise serializers.ValidationError(
                {"attribute_scope": "This field is required when tag_type is 'attribute'."}
            )
        return attrs


class GeneralSettingsSerializer(serializers.Serializer):
    lang = serializers.CharField(max_length=255, default="en")
    roomio_node_url = serializers.CharField(max_length=255, default="", allow_blank=True, allow_null=True)
    timezone = serializers.IntegerField(default=0)
    controllers_sync = serializers.BooleanField(default=False)
    guest_auto_block = serializers.BooleanField(default=False)
    guest_auto_block_time = serializers.TimeField(default=time(hour=12))
    check_in_out = serializers.BooleanField(default=False)
    vip_status = serializers.BooleanField(default=False)
    suite_rooms_controls_sync = serializers.BooleanField(default=False)
    laundry = serializers.BooleanField(default=False)
    visionline = serializers.BooleanField(default=False)
    opera_integration = serializers.BooleanField(default=False)
    visionline_card_system = serializers.BooleanField(default=False)
    aperio_locks = serializers.BooleanField(default=False)
    door_lock = DoorLockSerializer(required=False)
    auto_checkout = serializers.BooleanField(default=False)
    auto_checkout_time = serializers.TimeField(default=time(hour=12))
    aggregate_db = serializers.BooleanField(default=False)
    check_in_trigger_value = serializers.IntegerField(default=2, min_value=0)
    check_out_trigger_value = serializers.IntegerField(default=1, min_value=0)
    main_dashboard = serializers.PrimaryKeyRelatedField(
        queryset=Dashboard.objects.all(), required=False, many=False, allow_null=True
    )
    room_fields = TagSerializer(many=True, required=False)

    def validate_main_dashboard(self, value):
        if value is None:
            return value

        dashboard = Dashboard.objects.filter(id=value.id).first()
        if not dashboard:
            raise serializers.ValidationError({"main_dashboard": [f"Object with title={value} does not exist."]})
        return str(dashboard.id)

    def update(self, instance, validated_data):
        updated_by = validated_data.pop("updated_by", None)
        for key, value in validated_data.items():
            if isinstance(value, time):
                validated_data[key] = value.isoformat()
        additional_info = instance.additional_info or {}
        g_settings = additional_info.get("general_settings", {})
        g_settings.update(validated_data)
        additional_info["general_settings"] = g_settings
        instance.additional_info = additional_info
        if updated_by is not None:
            instance.updated_by = updated_by
        instance.save()
        return instance

    def to_representation(self, instance):
        g_settings = instance.additional_info.get("general_settings", {}) if instance.additional_info else {}

        for field_name, field in self.fields.items():
            if field_name == "main_dashboard":
                g_settings[field_name] = g_settings.get(field_name, None)
            elif field_name == "door_lock":
                g_settings[field_name] = g_settings.get(field_name, {"ving_card": False, "kaba": False})
            elif field_name == "room_fields":
                g_settings[field_name] = g_settings.get(field_name, [])
            else:
                g_settings[field_name] = g_settings.get(field_name, field.default)

        merged = {**g_settings}
        return {"tenant_id": instance.id, **merged}

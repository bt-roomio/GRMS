from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Device, Room, RoomType, Tenant
from main.serializers.device import SimpleDeviceSerializer
from main.serializers.general_settings import TagSerializer
from main.serializers.guest import SimpleGuestSerializer
from main.serializers.room_type import RoomTypeSerializer
from shuttle.models import AttributeKv


class RoomSerializer(serializers.ModelSerializer):
    tenant = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all(), required=False)
    type = serializers.PrimaryKeyRelatedField(queryset=RoomType.objects.all(), required=False)
    devices = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all(), many=True, required=False)
    door_lock_device_id = serializers.PrimaryKeyRelatedField(
        queryset=Device.objects.all(), required=False, source="door_lock_device", allow_null=True
    )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["additional_fields"] = instance.additional_fields if hasattr(instance, "additional_fields") else None
        data["telemetry"] = instance.ts_kv_values if hasattr(instance, "ts_kv_values") else None
        data["tenant"] = str(instance.tenant_id)
        data["devices"] = SimpleDeviceSerializer(instance.devices, many=True).data
        data["door_lock_device"] = (
            SimpleDeviceSerializer(instance.door_lock_device).data if instance.door_lock_device else None
        )
        if hasattr(instance, "count_online_devices"):
            data["status"] = (
                "ON"
                if instance.count_online_devices == instance.count_devices and instance.count_devices > 0
                else "OFF"
            )
        if self.context.get("detail"):
            data["type"] = RoomTypeSerializer(instance.type).data if instance.type else None
        else:
            data["type"] = instance.type and instance.type.title
        return data

    def update(self, instance, validated_data):

        for device in validated_data.get("devices", {}):
            if device.room_id and device.room_id != instance.id:
                raise serializers.ValidationError({"devices": "Device already assigned to another room!"})
        AttributeKv.objects.update_or_create_or_delete(validated_data.get("devices"), instance)  # pyright: ignore
        data = super().update(instance, validated_data)
        return data

    def create(self, validated_data):
        for device in validated_data.get("devices", {}):
            if device.room_id:
                raise serializers.ValidationError({"devices": "Device already assigned to another room!"})
        return super().create(validated_data)

    class Meta:
        model = Room
        fields = (
            "id",
            "created_at",
            "number",
            "label",
            "floor",
            "block",
            "type",
            "state",
            "public_area_id",
            "pan_id",
            "building",
            "door_lock_device_id",
            "suite",
            "tenant",
            "status",
            "devices",
            "additional_info",
        )


class SimpleRoomSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["tenant"] = instance.tenant_id
        data["type"] = instance.type_id
        return data

    class Meta:
        model = Room
        fields = (
            "id",
            "created_at",
            "number",
            "label",
            "floor",
            "block",
            "type",
            "state",
            "pan_id",
            "building",
            "door_lock_device",
            "suite",
            "tenant",
            "status",
            "additional_info",
        )


class RoomFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("created_at", "-created_at", "number", "floor", "block", "-number", "-floor", "-block")

    page = serializers.IntegerField(default=1, min_value=1)
    size = serializers.IntegerField(default=50, max_value=200)
    state = serializers.ChoiceField(choices=Room.STATE, required=False)
    status = serializers.ChoiceField(
        choices=Room.STATUS,
        required=False,
        error_messages={"invalid_choice": _('"{input}" is not a valid choice. Choose next: ON or OFF')},
    )
    search_field = serializers.ChoiceField(choices=("number", "floor", "block", "type__title"), required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
    tags = TagSerializer(many=True, required=False)

    def validate(self, attrs):
        if "search_field" not in attrs and "search_value" in attrs:
            raise serializers.ValidationError({"search_field": "search_field is required!"})

        if "search_value" not in attrs and "search_field" in attrs:
            raise serializers.ValidationError({"search_value": "search_value is required!"})
        return attrs


class RoomFilterParamsSwagger(serializers.Serializer):
    """Swagger-only version of RoomFilterParams without nested TagSerializer."""

    SORT_FIELDS = ("created_at", "-created_at", "number", "floor", "block", "-number", "-floor", "-block")

    page = serializers.IntegerField(default=1, min_value=1)
    size = serializers.IntegerField(default=50, max_value=200)
    state = serializers.ChoiceField(choices=Room.STATE, required=False)
    status = serializers.ChoiceField(
        choices=Room.STATUS,
        required=False,
        error_messages={"invalid_choice": _('"{input}" is not a valid choice. Choose next: ON or OFF')},
    )
    search_field = serializers.ChoiceField(choices=("number", "floor", "block", "type__title"), required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
    tags = serializers.JSONField(required=False, help_text="Array of tag objects with name, tag_type, attribute_scope")


class RoomDetailWsSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["telemetry"] = instance.ts_kv_values if hasattr(instance, "ts_kv_values") else None
        data["tenant"] = str(instance.tenant_id)
        data["devices"] = SimpleDeviceSerializer(instance.devices, many=True).data
        if hasattr(instance, "count_online_devices"):
            data["status"] = (
                "ON"
                if instance.count_online_devices == instance.count_devices and instance.count_devices > 0
                else "OFF"
            )
        if self.context.get("detail"):
            data["type"] = RoomTypeSerializer(instance.type).data if instance.type else None
        else:
            data["type"] = instance.type and instance.type.title
        data["guest"] = (
            SimpleGuestSerializer(instance.last_guests[0]).data
            if hasattr(instance, "last_guests") and instance.last_guests
            else None
        )
        return data

    class Meta:
        model = Room
        fields = ("id", "number", "floor", "block", "type", "state", "additional_info")

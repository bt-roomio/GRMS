from rest_framework import serializers

from access_manager.models import Card, GuestCard, NeedSyncDevice, StaffCard
from core.utils.serializers import ValidatorSerializer
from main.models import Device, PublicSpace
from main.serializers.device import SimpleDeviceSerializer


class NeedSyncDeviceSerializer(serializers.ModelSerializer):
    device_name = serializers.SerializerMethodField()
    card_number = serializers.SerializerMethodField()
    is_pwd = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()
    public_space = serializers.SerializerMethodField()
    room = serializers.SerializerMethodField()
    failed_requests_list = serializers.SerializerMethodField()
    message_params = serializers.SerializerMethodField()

    class Meta:
        model = NeedSyncDevice
        fields = [
            "created_at",
            "device_name",
            "card_number",
            "is_pwd",
            "user_name",
            "user_type",
            "public_space",
            "room",
            "failed_requests_list",
            "message_params",
        ]

    def get_message_params(self, obj):
        return (obj.additional_info or {}).get("message_params", {})

    def get_failed_requests_list(self, obj):
        return (obj.additional_info or {}).get("failed_requests", [])

    def get_device_name(self, obj):
        return getattr(obj.device, "name", None)

    def get_card_number(self, obj):
        return getattr(obj.card, "number", None)

    def get_is_pwd(self, obj):
        return getattr(obj.card, "is_pwd", False)

    def _get_active_staff_card(self, obj):
        if not obj.card_id:
            return None
        return StaffCard.objects.select_related("staff").filter(card_id=obj.card_id, is_active=True).first()

    def _get_active_guest_card(self, obj):
        if not obj.card_id:
            return None
        return GuestCard.objects.select_related("guest").filter(card_id=obj.card_id, is_active=True).first()

    def get_user_name(self, obj):
        staff_card = self._get_active_staff_card(obj)
        if staff_card:
            return staff_card.staff.get_name()

        guest_card = self._get_active_guest_card(obj)
        if guest_card:
            return guest_card.guest.get_name()

        return None

    def get_user_type(self, obj):
        if self._get_active_staff_card(obj):
            return "Staff"
        if self._get_active_guest_card(obj):
            return "Guest"
        return None

    def get_public_space(self, obj):
        if not obj.device_id:
            return None

        public_space = PublicSpace.objects.filter(device_public_spaces__device_id=obj.device_id).only("name").first()
        return f"Public Space: {public_space.name}" if public_space else None

    def get_room(self, obj):
        room = getattr(obj.device, "room", None)
        return f"Room {room.number}" if room else None


class NeedSyncDeviceFilterParams(ValidatorSerializer):
    sort_by = serializers.ListField(
        child=serializers.ChoiceField(choices=["-created_at", "created_at"], required=False),
        required=False,
        default=["-created_at"],
    )
    size = serializers.IntegerField(default=50, max_value=200)
    page = serializers.IntegerField(default=1, min_value=1)


class SyncDeviceSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=False,
        help_text="List of NeedSyncDevice UUIDs to sync. If not provided, all devices needing sync will be processed.",
    )
    device_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=False,
        help_text="List of Device UUIDs to sync. If not provided, all devices needing sync will be processed.",
    )


class SimpleNeedSyncDeviceSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = SimpleDeviceSerializer(instance, context={**self.context, "exclude_room_obj": False}).data
        data["message_params"] = self.context.get("message_params_map", {}).get(instance.id, {})
        return data

    class Meta:
        model = Device
        fields = ("id",)


class NeedSyncDeviceHttpFilterParams(ValidatorSerializer):
    card_id = serializers.PrimaryKeyRelatedField(queryset=Card.objects.all(), required=True)
    need_sync = serializers.BooleanField(required=False, allow_null=True, default=None)
    sort_by = serializers.ListField(
        child=serializers.ChoiceField(choices=["-created_at", "created_at"], default="-created_at"), required=False
    )
    size = serializers.IntegerField(default=50, max_value=200)
    page = serializers.IntegerField(default=1, min_value=1)

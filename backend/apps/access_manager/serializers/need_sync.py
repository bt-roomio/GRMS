from access_manager.models import Card, NeedSyncDevice

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.serializers.device import SimpleDeviceSerializer


class NeedSyncDeviceSerializer(serializers.ModelSerializer):
    device_name = serializers.SerializerMethodField()
    card_number = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()
    public_space = serializers.SerializerMethodField()
    room = serializers.SerializerMethodField()
    failed_requests_list = serializers.SerializerMethodField()

    class Meta:
        model = NeedSyncDevice
        fields = [
            "created_at",
            "device_name",
            "card_number",
            "user_name",
            "user_type",
            "public_space",
            "room",
            "failed_requests_list",
        ]

    def get_failed_requests_list(self, obj):
        failed_requests = obj.additional_info.get("failed_requests", [])
        return failed_requests

    def get_device_name(self, obj):
        return obj.device.name if obj.device else None

    def get_card_number(self, obj):
        return obj.card.number if obj.card else None

    def get_user_name(self, obj):
        staff_card = getattr(obj.card, "staffcard", None)
        if staff_card and staff_card.is_active:
            return staff_card.staff.get_name()

        guest_cards = obj.card.guestcard_set.filter(is_active=True)
        if guest_cards.exists():
            guest_card = guest_cards.first()
            guest_name = guest_card.guest.name
            if guest_card.guest.lastname:
                guest_name += f" {guest_card.guest.lastname}"
            return guest_name

        return None

    def get_user_type(self, obj):
        staff_card = getattr(obj.card, "staffcard", None)
        if staff_card and staff_card.is_active:
            return "Staff"

        guest_cards = obj.card.guestcard_set.filter(is_active=True)
        if guest_cards.exists():
            return "Guest"

        return None

    def get_public_space(self, obj):
        if not obj.device:
            return None

        public_spaces = obj.device.publicspace_set.all()
        if public_spaces.exists():
            return f"Public Space: {public_spaces.first().name}"
        return None

    def get_room(self, obj):
        if not obj.device:
            return None

        if obj.device.room:
            return f"Room {obj.device.room.number}"
        return None


class NeedSyncDeviceFilterParams(ValidatorSerializer):
    sort_by = serializers.ListField(
        child=serializers.ChoiceField(choices=["-created_at", "created_at"], default="-created_at", required=False)
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
        data = super().to_representation(instance)
        data["device"] = SimpleDeviceSerializer(instance.device).data
        holder = self.context.get("holder", {})
        data["staff_name"] = holder.get("name") if holder.get("type") == "staff" else None
        data["guest_name"] = holder.get("name") if holder.get("type") == "guest" else None
        return data

    class Meta:
        model = NeedSyncDevice
        fields = ("id", "created_at", "created_by_id", "updated_at", "updated_by", "need_sync", "device", "card")


class NeedSyncDeviceHttpFilterParams(ValidatorSerializer):
    card_id = serializers.PrimaryKeyRelatedField(queryset=Card.objects.all(), required=True)
    sort_by = serializers.ListField(
        child=serializers.ChoiceField(choices=["-created_at", "created_at"], default="-created_at"),
        required=False,
    )
    size = serializers.IntegerField(default=50, max_value=200)
    page = serializers.IntegerField(default=1, min_value=1)

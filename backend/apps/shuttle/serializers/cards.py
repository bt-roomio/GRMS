from access_manager.models import Card, Group, GuestCard, StaffCard
from access_manager.serializers.staff import StaffSerializer

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.serializers.guest import GuestSerializer
from main.serializers.room import SimpleRoomSerializer


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = (
            "id",
            "created_at",
            "name",
            "tenant",
            "end_time",
            "expiry_date",
            "is_active",
            "additional_info",
        )


class CardSerializer(serializers.Serializer):
    card_id = serializers.SerializerMethodField()
    created_at = serializers.CharField()
    need_to_sync = serializers.SerializerMethodField()
    number = serializers.CharField()
    is_active = serializers.BooleanField()
    card_user = serializers.SerializerMethodField()

    class Meta:
        model = Card
        fields = ["created_at", "card_id", "card_number", "need_to_sync", "is_active"]

    def get_card_user(self, obj):
        try:
            staff_card = StaffCard.objects.filter(card=obj, is_active=True).first()
            if staff_card:
                staff = staff_card.staff
                staff_serializer = StaffSerializer(staff)
                staff_group = staff.group
                group_serializer = None
                if staff_group:
                    group_serializer = GroupSerializer(staff_group).data
                return {"type": "staff", "user_data": staff_serializer.data, "group": group_serializer}

            guest_card = GuestCard.objects.filter(card=obj, is_active=True).first()
            if guest_card:
                guest = guest_card.guest
                guest_serializer = GuestSerializer(guest)
                room_serializer = SimpleRoomSerializer(guest.room)
                return {"type": "guest", "data": guest_serializer.data, "room": room_serializer.data}
            return None
        except Exception:
            return None

    def get_card_id(self, obj):
        return str(obj.id)

    def get_need_to_sync(self, obj):
        return obj.needsyncdevice_set.filter(need_sync=True).exists()


class CardFilterParams(ValidatorSerializer):
    SORT_FIELDS = (
        "created_at",
        "-created_at",
    )

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=20)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
    search_value = serializers.CharField(required=False, allow_null=True)
    filters = serializers.DictField(
        required=False,
        child=serializers.BooleanField()
    )

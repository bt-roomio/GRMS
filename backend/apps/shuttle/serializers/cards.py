from rest_framework import serializers

from access_manager.models import Card, StaffCard, GuestCard, Group

# from access_manager.serializers.group import GroupSerializer
from access_manager.serializers.staff import StaffSerializer
from core.utils.serializers import ValidatorSerializer
from main.serializers.guest import GuestSerializer


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
    need_to_sync = serializers.SerializerMethodField()
    number = serializers.CharField()
    card_user = serializers.SerializerMethodField()

    class Meta:
        model = Card
        fields = ["card_id", "card_number", "need_to_sync"]

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
                serializer = GuestSerializer(guest)
                return {"type": "guest", "data": serializer.data}
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

from rest_framework import serializers

from access_manager.models import GuestCard
from core.utils.serializers import ValidatorSerializer
from main.models import Room


class GuestCardSerializer(serializers.ModelSerializer):
    card_id = serializers.CharField(source="card.id")
    card_number = serializers.CharField(source="card.number")
    guest_name = serializers.SerializerMethodField()
    guest_check_in = serializers.IntegerField(source="guest.check_in")
    guest_id = serializers.CharField(source="guest.id")
    need_to_sync = serializers.SerializerMethodField()
    created_at = serializers.CharField()

    class Meta:
        model = GuestCard
        fields = ["card_id", "card_number", "guest_name", "guest_check_in", "guest_id", "need_to_sync", "created_at"]

    def get_guest_name(self, obj):
        guest = obj.guest
        if guest.lastname:
            return f"{guest.name} {guest.lastname}"
        return guest.name

    def get_need_to_sync(self, obj):
        return obj.card.needsyncdevice_set.filter(need_sync=True).exists()


class GuestCardFilterParams(ValidatorSerializer):
    SORT_FIELDS = (
        "created_at",
        "-created_at",
        "need_sync",
        "-need_sync",
    )

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)

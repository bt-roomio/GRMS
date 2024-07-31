from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Guest, Room


class GuestMoveRoomFilterParams(ValidatorSerializer):
    from_room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    to_room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())


class GuestMoveRoomSerializer(serializers.Serializer):
    to_room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())

    def update(self, instance, validated_data):
        for guest in instance:
            guest.room_id = validated_data.get("to_room")
            guest.save()
        return instance


class GuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guest
        fields = (
            "id",
            "name",
            "lastname",
            "gender",
            "nationality",
            "birthday",
            "is_active",
            "room",
            "check_in",
            "check_out",
            "auto_check_out",
            "reservation_number",
        )


class GuestFilterParams(ValidatorSerializer):
    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all(), required=False)

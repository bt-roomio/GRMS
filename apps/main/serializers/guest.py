from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Guest, Room


class GuestMoveRoomFilterParams(ValidatorSerializer):
    from_room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    to_room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())


class GuestMoveRoomSerializer(serializers.Serializer):
    to_room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    from_room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())

    def update(self, instance, validated_data):
        from_room = validated_data.pop("from_room")
        from_room.state.append(Room.Available)
        from_room.state.remove(Room.CheckedIn)
        from_room.save()

        for guest in instance:
            guest.room = validated_data.get("to_room")
            guest.save()

        to_room = validated_data.pop("to_room")
        to_room.state.append(Room.CheckedIn)
        to_room.state.remove(Room.Available)
        to_room.save()

        return instance


class GuestSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        instance = super().create(validated_data)

        room = instance.room
        if room and Room.CheckedIn not in room.state:
            if Room.Available in room.state:
                room.state.remove(Room.Available)
            room.state.append(Room.CheckedIn)
            room.save()
        return instance

    def update(self, instance, validated_data):
        old_room = instance.room_id and Room.objects.prefetch_related("guests").filter(id=instance.room_id).first()
        if old_room and len(old_room.guests.all()) == 1:
            if Room.Available in old_room.state:
                old_room.state.remove(Room.Available)
            old_room.state.append(Room.Available)
            old_room.save()

        new_room = validated_data.get("room") and Room.objects.filter(id=validated_data.get("room").id).first()
        if new_room and not new_room.guests.exists():
            if Room.Available in new_room.state:
                new_room.state.remove(Room.Available)
            new_room.state.append(Room.CheckedIn)
            new_room.save()
        return super().update(instance, validated_data)

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
        extra_kwargs = {
            "check_in": {"required": True},
            "check_out": {"required": True},
            "is_active": {"default": True},
        }


class GuestFilterParams(ValidatorSerializer):
    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all(), required=False)

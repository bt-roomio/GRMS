from rest_framework import serializers

from access_manager.models import Group, GroupRoom, TypeChoices
from access_manager.utilits.task_trigger import card_room
from main.models import Room


class HousekeepingRoomSerializer(serializers.Serializer):
    room_id = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    remove = serializers.BooleanField()

    def validate_room_id(self, value):
        if value.tenant_id != self.context["tenant_id"]:
            raise serializers.ValidationError("Room not found.")
        return value

    def validate(self, attrs):
        groups = Group.objects.filter(
            tenant_id=self.context["tenant_id"],
            group_type=TypeChoices.HOUSEKEEPING,
            is_active=True,
        )
        if not groups.exists():
            raise serializers.ValidationError("No active HOUSEKEEPING group found.")
        attrs["groups"] = list(groups)
        return attrs

    def save(self, **kwargs):
        room = self.validated_data["room_id"]
        remove = self.validated_data["remove"]
        groups = self.validated_data["groups"]

        action = "disconnect" if remove else "connect"

        for group in groups:
            if remove:
                card_room(group.id, room.id, action="disconnect")
                GroupRoom.objects.filter(group=group, room=room).delete()
            else:
                GroupRoom.objects.get_or_create(group=group, room=room)
                card_room(group.id, room.id, action="connect")

        return {"room_id": str(room.id), "action": action}

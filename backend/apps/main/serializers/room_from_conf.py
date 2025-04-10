from main.models import Room, RoomType
from rest_framework import serializers
from shuttle.utils.camel_to_snake import to_snake_case_data


class RoomConfigSerializer(serializers.Serializer):
    room_number = serializers.CharField()
    floor = serializers.CharField()
    block = serializers.CharField()
    room_type_name = serializers.CharField()
    public_area_id = serializers.IntegerField(required=False, allow_null=True)
    pan_id = serializers.CharField(required=False, allow_null=True)
    building = serializers.CharField(required=False, allow_null=True)
    door_lock_id = serializers.CharField(required=False, allow_null=True)


class RoomFromConfSerializer(serializers.Serializer):
    rooms = RoomConfigSerializer(many=True)

    def to_internal_value(self, data):
        rooms = [
            i
            for i in data.get("rooms", [])
            if all(key in i for key in ["roomNumber", "floor", "block", "roomTypeName"])
        ]
        data["rooms"] = rooms
        if not rooms:
            raise serializers.ValidationError({"detail": "No rooms found"})

        return super().to_internal_value(to_snake_case_data(data))

    def create(self, validated_data):
        result = {
            "rooms": [],
            "room_types": [],
        }
        tenant = self.context.get("tenant")
        rooms = validated_data.pop("rooms")
        result["rooms"] = rooms

        for room in rooms:
            room_type_name = room.get("room_type_name")
            room_type_obj, _ = RoomType.objects.get_or_create(title=room_type_name, tenant=tenant)

            Room.objects.get_or_create(
                number=room.get("room_number"),
                floor=room.get("floor"),
                block=room.get("block"),
                tenant=tenant,
                defaults={
                    "type": room_type_obj,
                    "public_area_id": room.get("public_area_id"),
                    "pan_id": room.get("pan_id"),
                    "building": room.get("building"),
                    "door_lock_id": room.get("door_lock_id"),
                    "state": [Room.Available],
                    "status": "OFF",
                },
            )
        return result

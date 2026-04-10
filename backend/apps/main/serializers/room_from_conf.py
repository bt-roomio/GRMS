from rest_framework import serializers

from main.models import Device, Room, RoomType


class RoomConfigSerializer(serializers.Serializer):
    number = serializers.IntegerField(required=True)
    floor = serializers.CharField(required=True)
    block = serializers.CharField(required=True)
    type = serializers.CharField(required=False, allow_null=True)
    devices = serializers.ListField(child=serializers.CharField(), required=False, default=[])

    def validate(self, attrs):
        missing_fields = [field for field in ["number", "floor", "block"] if not attrs.get(field)]
        if missing_fields:
            raise serializers.ValidationError(
                {field: f"{field.capitalize()} is a required field." for field in missing_fields}
            )
        return attrs


class RoomFromConfSerializer(serializers.Serializer):
    rooms = serializers.ListField(child=serializers.DictField(), allow_empty=False)

    def validate(self, attrs):
        self._validated_rooms = []
        self._invalid_rooms = []

        for room_data in attrs["rooms"]:
            serializer = RoomConfigSerializer(data=room_data)
            if serializer.is_valid():
                self._validated_rooms.append(serializer.validated_data)
            else:
                self._invalid_rooms.append(
                    {"room_number": room_data.get("number", "Unknown"), "errors": serializer.errors}
                )

        return attrs

    def create(self, validated_data):
        tenant = self.context.get("tenant")
        result = {"rooms": [], "errors": self._invalid_rooms[:], "device_errors": []}

        for room_data in self._validated_rooms:
            try:
                room_type_obj = None
                if room_data.get("type"):
                    room_type_obj, _ = RoomType.objects.get_or_create(title=room_data["type"], tenant=tenant)

                room, created = Room.objects.update_or_create(
                    number=room_data["number"],
                    floor=room_data["floor"],
                    block=room_data["block"],
                    tenant=tenant,
                    defaults={
                        "type": room_type_obj,
                        "state": [Room.Available],
                        "status": "OFF",
                    },
                )

                valid_device_found = False
                for device_mac in room_data.get("devices", []):
                    try:
                        device = Device.objects.get(tenant=tenant, name=device_mac, is_active=True)
                        device.room = room
                        device.save()
                        valid_device_found = True
                    except Device.DoesNotExist:
                        result["device_errors"].append(
                            {
                                "room_number": room.number,
                                "floor": room.floor,
                                "block": room.block,
                                "device_mac": device_mac,
                                "message": "Device not found",
                            }
                        )

                if valid_device_found or not room_data.get("devices"):
                    result["rooms"].append(
                        {"number": room.number, "floor": room.floor, "block": room.block, "status": "success"}
                    )

            except Exception as e:
                result["errors"].append({"room_number": room_data.get("number", "Unknown"), "message": str(e)})

        return result

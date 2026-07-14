from hoteza.utils.exception import JsonValidationError

from rest_framework import serializers

from main.models import Guest, Room, Tenant
from main.serializers.guest import GuestMoveRoomSerializer
from services.utils.const import HOTEZA


class GuestChangeSerializer(serializers.Serializer):
    hotelId = serializers.CharField()
    roomNumber = serializers.CharField()
    guestName = serializers.CharField()
    oldRoom = serializers.CharField(allow_null=True, allow_blank=True)
    guestFirstName = serializers.CharField()
    guestTitle = serializers.CharField(allow_null=True, allow_blank=True)
    pmsRegNum = serializers.CharField()
    departureDateTS = serializers.CharField()
    guestLanguage = serializers.CharField(allow_null=True, allow_blank=True)
    roomShare = serializers.CharField()
    swapFlag = serializers.CharField()
    profileNum = serializers.CharField(allow_null=True, allow_blank=True)

    @staticmethod
    def convert_fields(attrs):
        ret = {
            "hotelId": "hotel_id",
            "guestFirstName": "name",
            "guestName": "lastname",
            "oldRoom": "old_room",
            "roomNumber": "room_number",
            "arrivalDateTS": "check_in",
            "departureDateTS": "check_out",
            "guestTitle": "title",
            "pmsRegNum": "pms_reg_num",
            "guestLanguage": "language",
            "roomShare": "room_share",
            "swapFlag": "swap_flag",
            "profileNum": "profile_num",
        }
        return {ret[key]: value for key, value in attrs.items() if key in ret}

    def validate(self, attrs):
        attrs = self.convert_fields(attrs)

        # Validate tenant
        tenant = Tenant.objects.filter(
            integration__integrator=HOTEZA,
            integration__hotel_id=attrs.get("hotel_id"),
            integration__enable=True,
            integration__is_active=True,
        ).first()
        if not tenant:
            raise JsonValidationError({"result": 9, "message": "Your hotelId not registered!"})

        # Validate room
        room = Room.objects.filter(tenant=tenant, number=attrs["room_number"]).first()
        if not room:
            raise JsonValidationError({"result": 9, "message": f"Room {attrs['room_number']} not found!"})
        attrs["room"] = room
        # Validate old room
        old_room = (
            Room.objects.filter(tenant=tenant, number=attrs["old_room"]).first() if attrs.get("old_room") else None
        )
        if attrs["old_room"] and not old_room:
            raise JsonValidationError({"result": 9, "message": f"Room {attrs['old_room']} not found!"})
        attrs["old_room"] = old_room

        attrs["tenant"] = tenant
        return attrs

    def create(self, validated_data):
        instance = Guest.objects.filter(
            additional_info__pms_reg_num=validated_data.get("pms_reg_num"),
            is_active=True,
        )
        if not instance:
            raise JsonValidationError({"result": 9, "message": "There is no guest with pms_reg_num!"})

        if validated_data.get("old_room"):
            serializer = GuestMoveRoomSerializer(
                instance,
                data={"from_room": validated_data.get("old_room").id, "to_room": validated_data.get("room").id},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

        validated_data.pop("hotel_id")
        validated_data.pop("old_room")
        validated_data.pop("pms_reg_num")
        validated_data.pop("room_share")
        validated_data.pop("swap_flag")
        validated_data.pop("profile_num")
        validated_data.pop("room_number")
        validated_data.pop("old_room") if validated_data.get("old_room") else None

        instance.update(**validated_data)
        return instance

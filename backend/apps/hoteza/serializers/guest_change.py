from rest_framework import serializers

from hoteza.utils.exception import JsonValidationError
from main.models import Tenant, Room, Guest
from main.serializers.guest import GuestMoveRoomSerializer


class GuestChangeSerializer(serializers.Serializer):
    hotelId = serializers.CharField()
    roomNumber = serializers.CharField()
    guestName = serializers.CharField()
    oldNumber = serializers.CharField()
    guestFirstName = serializers.CharField()
    guestTitle = serializers.CharField()
    pmsRegNum = serializers.CharField()
    departureDateTS = serializers.CharField()
    guestLanguage = serializers.CharField()
    roomShare = serializers.CharField()
    swapFlag = serializers.CharField()
    profileNum = serializers.CharField()

    @staticmethod
    def convert_fields(attrs):
        ret = {
            "hotelId": "hotel_id",
            "guestFirstName": "name",
            "guestName": "lastname",
            "oldNumber": "old_number",
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

        tenant = Tenant.objects.filter(additional_info__general_settings__hotelId=attrs.get("hotel_id")).first()
        if not tenant:
            raise JsonValidationError({"result": 9, "message": "Your hotelId not registered!"})

        room = Room.objects.filter(tenant=tenant, number=attrs["room_number"]).first()
        old_room = Room.objects.filter(tenant=tenant, number=attrs["old_number"]).first()
        if not room or not old_room:
            none_room = attrs["room_number"] if not room else attrs["old_number"]
            raise JsonValidationError({"result": 9, "message": f"Room `{none_room}` not found!"})
        attrs["tenant"] = tenant
        attrs["to_room"] = room
        attrs["from_room"] = old_room
        return attrs

    def create(self, validated_data):
        instance = Guest.objects.filter(room=validated_data.get("from_room"), is_active=True)
        if not instance:
            raise JsonValidationError({"result": 9, "message": "There is no guest in the room!"})
        serializer = GuestMoveRoomSerializer(
            instance,
            data={"to_room": validated_data.get("to_room").id, "from_room": validated_data.get("from_room").id},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return instance

from rest_framework import serializers

from hoteza.utils.exception import JsonValidationError
from main.models import Tenant, Room
from main.serializers.guest import GuestSerializer


class CheckInSerializer(serializers.Serializer):
    hotelId = serializers.CharField()
    roomNumber = serializers.CharField()
    guestName = serializers.CharField()
    guestFirstName = serializers.CharField()
    guestTitle = serializers.CharField()
    pmsRegNum = serializers.CharField()
    arrivalDateTS = serializers.CharField()
    departureDateTS = serializers.CharField()
    guestLanguage = serializers.CharField()
    roomShare = serializers.CharField()
    swapFlag = serializers.CharField()
    nopost = serializers.CharField()
    profileNum = serializers.CharField()

    @staticmethod
    def convert_fields(attrs):
        ret = {
            "hotelId": "hotel_id",
            "guestFirstName": "name",
            "guestName": "lastname",
            "roomNumber": "room_number",
            "arrivalDateTS": "check_in",
            "departureDateTS": "check_out",
            "guestTitle": "title",
            "pmsRegNum": "pms_reg_num",
            "guestLanguage": "language",
            "roomShare": "room_share",
            "swapFlag": "swap_flag",
            "nopost": "no_post",
            "profileNum": "profile_num",
        }
        return {ret[key]: value for key, value in attrs.items() if key in ret}

    def validate(self, attrs):
        attrs = self.convert_fields(attrs)

        tenant = Tenant.objects.filter(additional_info__general_settings__hotelId=attrs.get("hotel_id")).first()
        if not tenant:
            raise JsonValidationError({"result": 9, "message": "Your hotelId not registered!"})

        room = Room.objects.filter(tenant=tenant, number=attrs["room_number"]).first()
        if not room:
            raise JsonValidationError({"result": 9, "message": "Room not found!"})
        attrs["tenant"] = tenant
        attrs["room"] = room
        return attrs

    def create(self, validated_data):
        guest_serializer = GuestSerializer()
        instance = guest_serializer.create(
            {
                "lastname": validated_data.pop("lastname"),
                "name": validated_data.pop("name"),
                "check_in": validated_data.pop("check_in"),
                "check_out": validated_data.pop("check_out"),
                "auto_check_out": True,
                "room": validated_data.pop("room"),
                "language": validated_data.pop("language"),
                "title": validated_data.pop("title"),
                "additional_info": validated_data,
                "tenant": validated_data.pop("tenant"),
            }
        )
        return instance

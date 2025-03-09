from hoteza.utils.exception import JsonValidationError

from rest_framework import serializers

from main.models import Guest, Room, Tenant
from main.serializers.guest import GuestSerializer


class CheckOutSerializer(serializers.Serializer):
    hotelId = serializers.CharField()
    roomNumber = serializers.CharField()
    pmsRegNum = serializers.CharField()
    roomShare = serializers.CharField()
    swapFlag = serializers.CharField()

    @staticmethod
    def convert_fields(attrs):
        ret = {
            "hotelId": "hotel_id",
            "roomNumber": "room_number",
            "pmsRegNum": "pms_reg_num",
            "roomShare": "room_share",
            "swapFlag": "swap_flag",
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
        guests = Guest.objects.filter(room=validated_data.get("room"))
        for guest in guests:
            data = {"is_active": False, "tenant": validated_data.get("tenant"), "room": validated_data.get("room")}
            serializer = GuestSerializer()
            serializer.update(guest, data)
        return guests

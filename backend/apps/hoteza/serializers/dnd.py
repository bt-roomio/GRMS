from hoteza.utils.exception import JsonValidationError

from rest_framework import serializers

from main.models import Room, Tenant


class DNDSerializer(serializers.Serializer):
    hotelId = serializers.CharField()
    roomNumber = serializers.CharField()
    pmsRegNum = serializers.CharField()
    dnd = serializers.IntegerField()

    def validate(self, attrs):
        attrs = self.convert_fields(attrs)

        tenant = Tenant.objects.filter(
            additional_info__integration_settings__hoteza__hotel_id=attrs.get("hotel_id"),
            additional_info__integration_settings__hoteza__enable=True,
        ).first()
        if not tenant:
            raise JsonValidationError({"result": 9, "message": "Your hotelId not registered!"})

        room = Room.objects.filter(tenant=tenant, number=attrs["room_number"]).first()
        if not room:
            raise JsonValidationError({"result": 9, "message": "Room not found!"})
        attrs["tenant"] = tenant
        attrs["room"] = room
        return attrs

    def create(self, validated_data):
        room = validated_data.get("room")
        room.state.append(Room.DoNotDisturb)
        room.save()
        return room

    @staticmethod
    def convert_fields(attrs):
        ret = {
            "hotelId": "hotel_id",
            "roomNumber": "room_number",
            "pmsRegNum": "pms_reg_num",
            "dnd": "dnd",
        }
        return {ret[key]: value for key, value in attrs.items() if key in ret}

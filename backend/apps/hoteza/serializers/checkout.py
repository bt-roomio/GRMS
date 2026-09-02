import logging

from hoteza.utils.exception import JsonValidationError

from rest_framework import serializers

from main.models import Guest, Room, Tenant
from main.serializers.guest import GuestSerializer
from services.utils.const import HOTEZA

logger = logging.getLogger(__name__)


class CheckOutSerializer(serializers.Serializer):
    hotelId = serializers.CharField(required=False)
    tenantId = serializers.CharField(required=False)
    roomNumber = serializers.CharField()
    pmsRegNum = serializers.CharField()
    roomShare = serializers.CharField()
    swapFlag = serializers.CharField()

    @staticmethod
    def convert_fields(attrs):
        ret = {
            "hotelId": "hotel_id",
            "tenantId": "tenant_id",
            "roomNumber": "room_number",
            "pmsRegNum": "pms_reg_num",
            "roomShare": "room_share",
            "swapFlag": "swap_flag",
        }
        return {ret[key]: value for key, value in attrs.items() if key in ret}

    def validate(self, attrs):
        logger.info("Validating CheckOut data: %s", attrs)
        attrs = self.convert_fields(attrs)
        tenant = None
        if attrs.get("hotel_id"):
            tenant = Tenant.objects.filter(
                integration__integrator__name__iexact=HOTEZA,
                integration__hotel_id=attrs.get("hotel_id"),
                integration__enable=True,
                integration__is_active=True,
            ).first()

        if not tenant and attrs.get("tenant_id"):
            tenant = Tenant.objects.filter(id=attrs.get("tenant_id")).first()

        if not tenant:
            raise JsonValidationError({"result": 9, "message": f"Tenant not found! ({attrs.get('tenant_id')})"})

        room = Room.objects.filter(tenant=tenant, number=attrs["room_number"]).first()
        if not room:
            raise JsonValidationError({"result": 9, "message": f"Room not found! ({attrs.get('room_number')})"})
        attrs["tenant"] = tenant
        attrs["room"] = room
        return attrs

    def create(self, validated_data):
        guests = Guest.objects.filter(
            additional_info__pms_reg_num=validated_data.get("pms_reg_num"),
            is_active=True,
        )
        result = None
        for guest in guests:
            data = {"is_active": False, "tenant": validated_data.get("tenant"), "room": validated_data.get("room")}
            serializer = GuestSerializer()
            result = serializer.update(guest, data)
        return result or guests

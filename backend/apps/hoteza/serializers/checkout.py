from access_manager.models import GuestCard
from access_manager.views.guest_card import prepare_cards, prepare_mqtt_request
from hoteza.utils.exception import JsonValidationError

from rest_framework import serializers

from main.models import Guest, Room, Tenant, Device
from main.serializers.guest import GuestSerializer


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
        attrs = self.convert_fields(attrs)
        tenant = None
        if attrs.get("hotel_id"):
            tenant = Tenant.objects.filter(
                additional_info__integration_settings__hoteza__hotel_id=attrs.get("hotel_id"),
                additional_info__integration_settings__hoteza__enable=True,
            ).first()

        if not tenant and attrs.get("tenant_id"):
            tenant = Tenant.objects.filter(id=attrs.get("tenant_id")).first()

        if not tenant:
            raise JsonValidationError({"result": 9, "message": "Tenant not found!"})

        room = Room.objects.filter(tenant=tenant, number=attrs["room_number"]).first()
        if not room:
            raise JsonValidationError({"result": 9, "message": "Room not found!"})
        attrs["tenant"] = tenant
        attrs["room"] = room
        return attrs

    def create(self, validated_data):
        guests = Guest.objects.filter(
            additional_info__pms_reg_num=validated_data.get("pms_reg_num"),
            is_active=True,
        )
        room = validated_data.get("room")
        cards = GuestCard.objects.filter(guest__in=guests, is_active=True).values_list("card__number", flat=True)
        device = Device.objects.filter(room__id=room.id, is_active=True).select_related("tenant").first()
        rpc_params = prepare_cards(cards, 0)
        deactivate_result = prepare_mqtt_request(device, rpc_params, cards, guests=guests, guest=None)
        if deactivate_result.get("success"):
            for guest in guests:
                data = {"is_active": False, "tenant": validated_data.get("tenant"), "room": validated_data.get("room")}
                serializer = GuestSerializer()
                serializer.update(guest, data)
            return guests
        return deactivate_result

import logging
import time

from django.db.models.signals import post_save

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq

from access_manager.models import GuestCard, Card
from access_manager.serializers.guest_card import GuestCardRequestSerializer
from access_manager.swagger.guest_card import guest_card_swagger
from core.utils.str_to_dict import str_to_dict
from shuttle.models import RPCMessage, Relation
from shuttle.utils.permissions import WhiteListOrIsAuthenticated


logger = logging.getLogger("main")


class GuestCardView(APIView):

    @guest_card_swagger()
    def post(self, request):
        from main.models import Guest, Device

        serializer = GuestCardRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            validated_data = serializer.validated_data
            tenant_id = request.user.tenant_id
            guest_id = validated_data["guest_id"]
            cards = validated_data["cards"]
            public_spaces = validated_data["public_spaces"]

            guest = Guest.objects.get(pk=guest_id)
            device = Device.objects.filter(room__guests=guest_id, is_active=True).first()

            if not guest:
                return Response({"detail": "Not found guest."}, 404)

            if not device:
                return Response({"detail": "Not found device."}, 404)

            rpc_params = prepare_cards(cards, 1)
            result = prepare_mqtt_request(device, rpc_params, cards, guests=None, guest=guest)
            return Response(result)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def prepare_cards(cards, access):
    rpc_params = []
    for card_number in cards:
        card_data = {
            "cardNumber": card_number,
            "access_group": str(access),
            "start_time": "00:00",
            "end_time": "23:59",
            "weekdays": ["1", "2", "3", "4", "5", "6", "7"],
            "slot_num": "1",
        }
        rpc_params.append(card_data)
    return rpc_params


def deactivate_guest_card(guests):
    try:
        for guest in guests:
            instance = GuestCard.objects.filter(guest=guest, is_active=True).update(is_active=False)
            post_save.send(
                sender=GuestCard,
                instance=instance,
                created=False,  # This is an update, not creation
                update_fields=["is_active"],
            )
        return {"success": True, "error_guest_cards": 0, "message": "Card is deactivated."}
    except Exception:
        return {"success": False, "message": "Could not disconnect card, please try again !"}


def prepare_mqtt_request(device, rpc_params, cards, guests=None, guest=None):
    from main.models import Device

    relation = Relation.objects.filter(to_id_id=device.id).order_by("updated_at").last()
    device_id = relation and relation.from_id.id
    gateway_or_none = Device.objects.gateway_or_none(device.id)
    rpc_message = RPCMessage.objects.create(additional_info={})
    request_id = rpc_message.id

    message = {
        "targetDeviceUUID": (gateway_or_none and str(gateway_or_none.id)) or str(device_id),
        "topic": "v1/gateway/rpc",
        "data": {
            "device": str(device.name),
            "data": {"id": request_id, "method": "writeRFID", "params": rpc_params, "timeout": 10000},
        },
    }
    logger.debug(message)

    if not rpc_params:
        return {"success": False, "cards_empty": True, "message": "Cards doesn't exist. "}

    channel = connect_to_rabbitmq()
    send_to_rabbitmq(channel, message)

    timeout_seconds = 5
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        has_message = RPCMessage.objects.filter(id=request_id, received=True).first()
        if has_message and str_to_dict(has_message.additional_info).get("success") == True and guests is not None:
            result = deactivate_guest_card(guests)
            return result
        if has_message and str_to_dict(has_message.additional_info).get("success") == True and guest is not None:
            result = activate_guest_card(cards, guest)
            return result

        time.sleep(1)

    return {"success": False, "message": "Could not perform action with card, please try again !"}


def activate_guest_card(cards, guest):
    for card_number in cards:
        card, _ = Card.objects.get_or_create(number=card_number, defaults={"tenant_id": guest.tenant_id})

        if GuestCard.objects.filter(guest=guest, card=card, is_active=True).exists():
            continue
        GuestCard.objects.create(guest=guest, card=card, is_active=True)

    return {
        "success": True,
        "message": "Successfully activated guest card.",
    }

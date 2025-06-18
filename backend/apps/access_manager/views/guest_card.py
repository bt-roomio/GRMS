import logging
import time

from access_manager.models import Card, GuestCard, NeedSyncDevice
from access_manager.serializers.guest_card import GuestCardRequestSerializer
from access_manager.swagger.guest_card import guest_card_swagger

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from access_manager.utilits.need_sync import need_sync
from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from core.utils.str_to_dict import str_to_dict
from shuttle.models import Relation, RPCMessage

logger = logging.getLogger("main")


class GuestCardView(APIView):

    @guest_card_swagger()
    def post(self, request):
        from main.models import Device, Guest

        serializer = GuestCardRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, 400)
        try:
            validated_data = serializer.validated_data

            if not validated_data or not isinstance(validated_data, dict):
                return Response({"detail": "Incorrect data!"}, 400)

            guest_id = validated_data["guest_id"]
            cards = validated_data["cards"]

            guest = Guest.objects.get(pk=guest_id)
            device = Device.objects.filter(room__guests=guest_id, is_active=True).first()

            if not guest:
                return Response({"detail": "Not found guest."}, 404)

            if not device:
                return Response({"detail": "Not found device."}, 404)

            rpc_params = prepare_cards(cards, 1)
            result = prepare_mqtt_request(device, rpc_params, cards, guests=None, guest=guest)
            if not result.get("success", True):
                return Response(result, status=400)
            return Response(result, status=200)

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


def deactivate_guest_card(cards):
    error_cards = []
    for card in cards:
        try:
            instance = GuestCard.objects.get(card__number=card, is_active=True)
            instance.is_active = False
            instance.save(update_fields=["is_active"])
        except Exception:
            error_cards.append(card)
    message = "Some cards are not deactivated."
    return {
        "success": error_cards == [],
        "error_cards": error_cards,
        "message": message if error_cards else "Cards are deactivated.",
    }


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

    if not rpc_params:
        return {"success": False, "cards_empty": True, "message": "Cards are not provided ! "}

    channel = connect_to_rabbitmq()
    send_to_rabbitmq(channel, message)

    timeout_seconds = 5
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        has_message = RPCMessage.objects.filter(id=request_id, received=True).first()
        is_success = str_to_dict(has_message.additional_info).get("success") if has_message else False
        if has_message and guests is not None:
            if is_success:
                result = deactivate_guest_card(cards)
                return result
            else:
                need_sync(cards, device, message)
        if has_message and is_success and guest is not None:
            result = activate_guest_card(cards, device, guest)
            return result

        time.sleep(1)
    else:
        need_sync(cards, device, message)
        return {"success": False, "message": "Timed out error !"}


def activate_guest_card(cards, device, guest):
    error_cards = []
    for card_number in cards:
        try:
            card, _ = Card.objects.get_or_create(number=card_number, defaults={"tenant_id": guest.tenant_id})

            if GuestCard.objects.filter(guest=guest, card=card, is_active=True).exists():
                continue
            GuestCard.objects.create(guest=guest, card=card, is_active=True)
            NeedSyncDevice.objects.filter(card=card, device=device).update(need_sync=False)
        except Exception as e:
            error_cards.append(card_number)
    message = "Some cards are not activated."
    return {
        "success": error_cards == [],
        "error_cards": error_cards,
        "message": message if error_cards else "Successfully activated guest card.",
    }

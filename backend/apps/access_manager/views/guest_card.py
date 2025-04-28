import logging
import time

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq

from access_manager.models import GuestCard, Card
from access_manager.serializers.guest_card import GuestCardRequestSerializer
from access_manager.swagger.guest_card import guest_card_swagger
from main.models import Guest
from shuttle.models import RPCMessage
from shuttle.utils.permissions import WhiteListOrIsAuthenticated


logger = logging.getLogger("main")


class GuestCardView(APIView):
    # permission_classes = (WhiteListOrIsAuthenticated,)

    @guest_card_swagger()
    def post(self, request):
        serializer = GuestCardRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            validated_data = serializer.validated_data
            guest_id = validated_data["guest_id"]
            cards = validated_data["cards"]
            public_spaces = validated_data["public_spaces"]

            rpc_params = []
            for card_number in cards:
                card_data = {
                    "cardNumber": card_number,
                    "access_group": "0",
                    "start_time": "00:00",
                    "end_time": "23:59",
                    "weekdays": ["1", "2", "3", "4", "5", "6", "7"],
                    "slot_num": "1",
                }
                rpc_params.append(card_data)
            result = prepare_mqtt_request(guest_id, rpc_params, cards)
            return Response(result)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def prepare_mqtt_request(guest_id, rpc_params, cards):
    guest = Guest.objects.get(pk=guest_id)
    tenant_id = guest.tenant.id
    rpc_message = RPCMessage.objects.create(additional_info={})
    request_id = rpc_message.id

    message = {
        "topic": "v1/gateway/rpc",
        "data": {"id": request_id, "method": "writeRFID", "params": rpc_params, "timeout": 5000},
    }
    logger.debug(message)

    channel = connect_to_rabbitmq()
    send_to_rabbitmq(channel, message)

    timeout_seconds = 5
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        has_message = RPCMessage.objects.filter(id=request_id, received=True).first()

        if has_message and has_message.additional_info.get("success") == True:
            for card_number in cards:
                card, _ = Card.objects.get_or_create(number=card_number, defaults={"tenant_id": tenant_id})
                GuestCard.objects.create(guest=guest, card=card)

            return {"success": True, "error_rooms": False, "error_public_spaces": []}
        time.sleep(0.3)

    return {"success": False, "error_rooms": False, "error_public_spaces": [], "msg": "Timeout error"}

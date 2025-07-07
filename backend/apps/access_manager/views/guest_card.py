import logging

from access_manager.models import StaffCard
from access_manager.serializers.guest_card import GuestCardRequestSerializer
from access_manager.swagger.guest_card import guest_card_swagger

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("main")


class GuestCardView(APIView):

    @guest_card_swagger()
    def post(self, request):
        from access_manager.tasks.send_rpc import send_rpc_request
        from main.models import Device

        serializer = GuestCardRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, 400)
        try:
            validated_data = serializer.validated_data

            if not validated_data or not isinstance(validated_data, dict):
                return Response({"detail": "Incorrect data!"}, 400)

            guest_id = validated_data["guest_id"]
            cards = validated_data["cards"]

            staff_cards = StaffCard.objects.filter(is_active=True, card__number__in=cards,
                                                   staff__tenant_id=request.user.tenant_id)
            if staff_cards:
                return Response({"message": "Card is connected to staff."}, 403)

            device = Device.objects.filter(room__guests=guest_id, is_active=True).first()

            if not device:
                return Response({"detail": "Not found device."}, 404)

            result = send_rpc_request(str(device.id), cards, 1, guest_id=guest_id)
            if not result.get("success", True):
                return Response(result, status=400)
            return Response(result, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


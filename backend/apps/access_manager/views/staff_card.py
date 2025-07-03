import logging
from typing import cast

from access_manager.models import GroupPublicSpace, GroupRoom, GuestCard
from access_manager.serializers.staff_card import StaffCardRequestData, StaffCardRequestSerializer
from access_manager.swagger.staff_card import staff_card_swagger

from rest_framework.response import Response
from rest_framework.views import APIView

from access_manager.utilits.send_rpc import send_rpc_request
from main.models import Device

logger = logging.getLogger("main")


class StaffCardView(APIView):
    @staff_card_swagger()
    def post(self, request):
        serializer = StaffCardRequestSerializer(data=request.data, context={"tenant_id": request.user.tenant_id})
        serializer.is_valid(raise_exception=True)

        try:
            validated_data = cast(StaffCardRequestData, serializer.validated_data)
            staff = validated_data["staff_id"]
            cards = validated_data["cards"]
            group = staff.group

            guest_cards = GuestCard.objects.filter(is_active=True, card__number__in=cards,
                                                   guest__tenant_id=request.user.tenant_id)
            if guest_cards:
                return Response({"message": "Card is connected to guest."}, 403)

            group_rooms_devices = GroupRoom.objects.filter(group=group, room__devices__is_active=True).values_list(
                "room__devices", flat=True
            )
            group_pub_spaces_devices = GroupPublicSpace.objects.filter(
                group=group, public_space__device__is_active=True
            ).values_list("public_space__device", flat=True)

            devices = Device.objects.filter(id__in=[*group_rooms_devices, *group_pub_spaces_devices])

            if not devices:
                return Response({"detail": "Not found device."}, 404)

            results = []
            for device in devices:
                result = send_rpc_request(str(device.id), cards, True, staff_id=str(staff.id))
                results.append(result)
            return Response(results)

        except Exception as e:
            return Response({"error": str(e)})

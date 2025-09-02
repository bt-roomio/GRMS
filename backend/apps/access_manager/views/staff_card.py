import logging
from typing import cast

from access_manager.models import GroupPublicSpace, GroupRoom, GuestCard, StaffCard
from access_manager.serializers.staff_card import StaffCardRequestData, StaffCardRequestSerializer
from access_manager.swagger.staff_card import staff_card_swagger

from rest_framework.response import Response
from rest_framework.views import APIView

from access_manager.tasks.send_rpc import send_rpc_request
from access_manager.utilits.check_card_assignment import get_card_assignments
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
            user = str(request.user.id)
            tenant_id = request.user.tenant_id
            group = staff.group

            errors = []
            success = []

            assigned_cards = get_card_assignments(cards=cards, tenant_id=tenant_id, exclude_staff=staff)

            if assigned_cards:
                return Response({"success": False, "message": f"Card is already assigned .",
                                 "assigned_cards": assigned_cards}, 403)

            group_rooms_devices = GroupRoom.objects.filter(group=group, room__devices__is_active=True).values_list(
                "room__devices", flat=True
            )
            group_pub_spaces_devices = GroupPublicSpace.objects.filter(
                group=group,
                public_space__device_public_spaces__device__is_active=True
            ).values_list("public_space__device_public_spaces__device", flat=True)

            devices = Device.objects.filter(id__in=[*group_rooms_devices, *group_pub_spaces_devices], is_active=True)

            if not devices:
                return Response({"detail": "Not found device."}, 404)

            for device in devices:
                result = send_rpc_request(str(device.id), cards, True, staff_id=str(staff.id), user=user)
                if not result.get("success", False):
                    errors.append(result)
                else:
                    success.append(result)

            if not errors:
                return Response({"success": True, "message": "Cards connected successfully !"}, status=200)
            return Response(
                {"message": "Couldn't synchronize the card with all devices !", "errors": errors, "success": success},
                status=400)

        except Exception as e:
            return Response({"error": str(e)})

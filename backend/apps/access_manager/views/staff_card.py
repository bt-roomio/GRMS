import logging
from typing import cast

from access_manager.serializers.staff_card import StaffCardRequestData, StaffCardRequestSerializer
from access_manager.swagger.staff_card import staff_card_swagger
from access_manager.tasks.send_rpc import send_rpc_request
from access_manager.utilits.check_card_assignment import get_card_assignments

from rest_framework.response import Response
from rest_framework.views import APIView

from main.utils.access_context import get_staff_access_context

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
            errors = []
            success = []

            assigned_cards = get_card_assignments(cards=cards, tenant_id=tenant_id, exclude_staff=staff)

            if assigned_cards:
                return Response({"success": False, "message": "Card is already assigned .",
                                 "assigned_cards": assigned_cards}, 403)

            access_context = get_staff_access_context(staff)
            devices = access_context.get("devices", [])

            if not devices:
                return Response({"detail": "Not found device."}, 404)

            for device in devices:
                result = send_rpc_request(str(device.id), cards, True, staff_id=str(staff.id), user=user)
                success.append(result) if result.get("success") else errors.append(result)
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

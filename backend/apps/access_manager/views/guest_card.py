import logging

from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from access_manager.models import GuestPublicSpace
from access_manager.serializers.guest_card import GuestCardRequestSerializer
from access_manager.swagger.guest_card import guest_card_swagger
from access_manager.utilits.check_card_assignment import get_card_assignments
from main.models import Guest

logger = logging.getLogger("main")


class GuestCardView(APIView):

    @guest_card_swagger()
    def post(self, request):
        from access_manager.tasks.send_rpc import send_rpc_request
        from main.utils.access_context import get_guest_access_context

        serializer = GuestCardRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, 400)

        try:
            validated_data = serializer.validated_data

            if not validated_data or not isinstance(validated_data, dict):
                return Response({"message": "Incorrect data!"}, 400)

            tenant_id = request.user.tenant_id
            guest_id = validated_data["guest_id"]
            public_spaces = validated_data["public_spaces"]
            cards = validated_data["cards"]
            is_pwd = validated_data.get("is_pwd", False)
            user = str(request.user.id)

            assigned_cards = get_card_assignments(
                cards=cards, tenant_id=tenant_id, exclude_guest_id=guest_id
            )

            if assigned_cards:
                return Response(
                    {
                        "success": False,
                        "message": "Card is already assigned.",
                        "assigned_cards": assigned_cards,
                    },
                    403,
                )
            guest = get_object_or_404(Guest, id=guest_id)

            for public_space in public_spaces:
                GuestPublicSpace.objects.get_or_create(
                    guest_id=guest_id, public_space_id=public_space
                )

            context = get_guest_access_context(guest)

            if not context:
                return Response({"message": "Guest not found."}, 404)

            devices = context.get("devices")

            if not devices.exists():
                return Response({"message": "Not found device."}, 404)

            errors = []
            success = []

            for device in devices:
                result = send_rpc_request(
                    str(device.id), cards, 1, guest_id=guest_id, user=user, is_pwd=is_pwd
                )
                if not result.get("success", False):
                    errors.append(result)
                else:
                    success.append(result)

            if not errors:
                return Response(
                    {"success": True, "message": "Cards connected successfully!"}, 200
                )
            return Response(
                {
                    "message": "Couldn't synchronize the card with all devices!",
                    "errors": errors,
                    "success": success,
                },
                400,
            )

        except Exception as e:
            logger.exception("Error in GuestCardView")
            return Response({"message": "Server error!", "error": str(e)}, 500)

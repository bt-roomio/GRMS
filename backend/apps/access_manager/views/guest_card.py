import logging

from access_manager.models import GuestPublicSpace
from access_manager.serializers.guest_card import GuestCardRequestSerializer
from access_manager.swagger.guest_card import guest_card_swagger
from access_manager.utilits.check_card_assignment import get_card_assignments
from django.db.models import Q

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
                return Response({"message": "Incorrect data!"}, 400)

            tenant_id = request.user.tenant_id
            guest_id = validated_data["guest_id"]
            public_spaces = validated_data["public_spaces"]
            cards = validated_data["cards"]
            user = str(request.user.id)
            errors = []
            success = []

            assigned_cards = get_card_assignments(cards=cards, tenant_id=tenant_id, exclude_guest_id=guest_id)

            if assigned_cards:
                return Response(
                    {"success": False, "message": f"Card is already assigned .", "assigned_cards": assigned_cards}, 403
                )

            for public_space in public_spaces:
                _, _ = GuestPublicSpace.objects.get_or_create(guest_id=guest_id, public_space_id=public_space)

            devices = Device.objects.filter(
                Q(room__guests=guest_id)
                | Q(device_public_spaces__public_space__in=public_spaces)
                | Q(device_public_spaces__public_space__room_type_public_spaces__room_type__room__guests=guest_id),
                is_active=True,
            ).distinct()

            if not devices:
                return Response({"message": "Not found device."}, 404)

            for device in devices:
                result = send_rpc_request(str(device.id), cards, 1, guest_id=guest_id, user=user)
                if not result.get("success", False):
                    errors.append(result)
                else:
                    success.append(result)

            if not errors:
                return Response({"success": True, "message": "Cards connected successfully !"}, status=200)
            return Response(
                {"message": "Couldn't synchronize the card with all devices !", "errors": errors, "success": success},
                status=400,
            )

        except Exception as e:
            return Response(
                {"message": "Server error !", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

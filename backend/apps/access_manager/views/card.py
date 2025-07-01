import logging
import random

from access_manager.models import Card, StaffCard, GuestCard, GroupRoom, GroupPublicSpace, GuestPublicSpace, \
    NeedSyncDevice
from access_manager.serializers.card import CardFilterParams, CardSerializer, DisconnectCardSerializer
from access_manager.swagger.card import card_swagger, swagger_card_disconnect
from access_manager.tasks import card_room, card_public_space
from access_manager.views.guest_card import prepare_cards, prepare_mqtt_request

from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.pagination import pagination
from core.utils.perform_request import with_tenant
from core.utils.permission import check_perms
from main.models import Device

logger = logging.getLogger(__name__)


class CardListView(APIView):
    @card_swagger()
    @check_perms(["access_manager.view_card"])
    def get(self, request):
        params = CardFilterParams.check(request.GET)
        queryset = Card.objects.list(  # pyright: ignore
            tenant_id=request.user.tenant_id,
            sort_by=params.get("sort_by", []),  # pyright: ignore
            search_field=params.get("search_field"),  # pyright: ignore
            search_value=params.get("search_value"),  # pyright: ignore
        )
        serializer = CardSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))  # pyright: ignore
        return Response(data)

    @card_swagger()
    @check_perms(["access_manager.add_card"])
    def post(self, request):
        data = with_tenant(request)
        card_number = random.randint(1, 99999999)
        data["number"] = card_number
        serializer = CardSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
        return Response(serializer.data, 201)


class CardDetailView(APIView):
    @card_swagger()
    @check_perms(["access_manager.view_card"])
    def get(self, request, pk):
        instance = get_object_or_404(Card, pk=pk, tenant_id=request.user.tenant_id)
        serializer = CardSerializer(instance)
        return Response(serializer.data)

    @card_swagger()
    @check_perms(["access_manager.change_card"])
    def put(self, request, pk):
        data = with_tenant(request)
        instance = get_object_or_404(Card, id=pk, tenant_id=request.user.tenant_id)
        serializer = CardSerializer(instance, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @card_swagger()
    @check_perms(["access_manager.delete_card"])
    def delete(self, request, pk):
        instance = get_object_or_404(Card, id=pk, tenant_id=request.user.tenant_id)
        result = disconnect_card(instance)
        if result:
            instance.is_active = False
            instance.save()
            return Response({}, 204)
        return Response({}, 204)


class DisconnectCardView(APIView):
    @swagger_card_disconnect()
    def post(self, request):
        serializer = DisconnectCardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        if isinstance(result, dict) and not result.get("success", True):
            return Response(result, status=400)

        return Response({"success": True, "message": f"Card is deactivated !"}, status=200)


def disconnect_card(card):
    try:
        deactivate = True
        card_num = str(card.number)

        staff_cards = StaffCard.objects.filter(card=card, is_active=True).select_related('staff', 'staff__group')
        guest_cards = GuestCard.objects.filter(card=card, is_active=True).select_related('guest', 'guest__room')

        for staff_card in staff_cards:
            if staff_card.staff.group:
                group = staff_card.staff.group
                group_rooms = GroupRoom.objects.filter(group=group)
                for group_room in group_rooms:
                    card_room(group.id, group_room.room.id, "disconnect", card_num)

                group_public_spaces = GroupPublicSpace.objects.filter(group=group)
                for group_public_space in group_public_spaces:
                    card_public_space(group.id, group_public_space.public_space.id, "disconnect", card_num)
                staff_card.is_active = False
                staff_card.save()

        for guest_card in guest_cards:
            guest = guest_card.guest

            if guest.room:
                room_devices = Device.objects.filter(room=guest.room, is_active=True)
                for device in room_devices:
                    rpc_params = prepare_cards([card_num], 0, device)
                    prepare_mqtt_request.delay(None, rpc_params, [card_num], guests=True, guest=None,
                                                        device_id=str(device.id))
            guest_public_spaces = GuestPublicSpace.objects.filter(guest=guest).select_related('public_space')
            for guest_public_space in guest_public_spaces:
                public_space = guest_public_space.public_space
                if public_space.device and public_space.device.is_active:
                    rpc_params = prepare_cards([card_num], 0, public_space.device)
                    prepare_mqtt_request.delay(None, rpc_params, [card_num],
                                                        guests=True, guest=None, device_id=str(public_space.device.id))

        need_sync_objs = NeedSyncDevice.objects.filter(card=card, need_sync=True).exists()

        if need_sync_objs:
            deactivate = False
        return deactivate

    except Exception as e:
        logger.error("Error disconnecting card %s: %s", {card.id}, {str(e)})
        return False

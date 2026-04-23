from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from access_manager.models import GuestCard
from access_manager.tasks.send_rpc import send_rpc_request
from core.utils.permission import check_perms
from main.models import Guest
from main.serializers.guest import GuestMoveRoomFilterParams, GuestMoveRoomSerializer
from main.utils.access_context import get_guest_access_context


class GuestMoveRoomListView(APIView):
    @swagger_auto_schema(
        tags=["Main, Guest Move Room"],
        responses={
            200: '"detail": "Guests moved successfully!"',
            404: '"detail": "\'from_room\' guests doesn\'t exist!"',
        },
        query_serializer=GuestMoveRoomFilterParams(),
    )
    @check_perms(["main.change_guestmoveroom"])
    def put(self, request):
        params = GuestMoveRoomFilterParams.check(request.GET)
        from_room = params.get("from_room")
        to_room = params.get("to_room")
        instance = Guest.objects.filter(room_id=from_room, is_active=True)
        if not instance.exists():
            return Response({"detail": "`from_room` guests doesn't exist!"}, 404)

        guests_list = list(instance)
        old_context = get_guest_access_context(guests_list)

        serializer = GuestMoveRoomSerializer(
            instance, data={"to_room": to_room.id, "from_room": from_room.id}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        moved_guests = list(Guest.objects.filter(id__in=[g.id for g in guests_list]))
        new_context = get_guest_access_context(moved_guests)

        old_device_ids = {str(d.id) for d in old_context["devices"]}
        new_device_ids = {str(d.id) for d in new_context["devices"]}
        shared_ids = old_device_ids & new_device_ids
        remove_ids = old_device_ids - shared_ids
        assign_ids = new_device_ids - shared_ids

        if not remove_ids and not assign_ids:
            return Response({"detail": "Guests moved successfully!"}, 200)

        guest_card_map: dict = {}
        for gc in GuestCard.objects.filter(guest__in=guests_list, is_active=True).select_related("card"):
            guest_card_map.setdefault(gc.guest_id, []).append(gc.card.number)

        for guest in guests_list:
            cards = guest_card_map.get(guest.id, [])
            if not cards:
                continue
            for device_id in remove_ids:
                send_rpc_request.delay(device_id, cards, 0, guest_id=str(guest.id))
            for device_id in assign_ids:
                send_rpc_request.delay(device_id, cards, 1, guest_id=str(guest.id))

        return Response({"detail": "Guests moved successfully!"}, 200)

from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_perms
from main.models import Guest
from main.serializers.guest import GuestMoveRoomFilterParams, GuestMoveRoomSerializer


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

        serializer = GuestMoveRoomSerializer(instance, data={"to_room": to_room.id, "from_room": from_room.id})  # ty: ignore
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"detail": "Guests moved successfully!"}, 200)
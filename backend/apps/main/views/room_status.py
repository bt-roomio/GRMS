from drf_yasg.utils import swagger_auto_schema

from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_perms
from main.models import Room
from main.serializers.room_status import RoomHistoryStatusSerializer


class RoomHistoryStatusView(APIView):
    @swagger_auto_schema(
        tags=["Main, Room History Status"],
        operation_description="Retrieve the status of rooms and their counts for the current tenant.",
        responses={
            200: RoomHistoryStatusSerializer(many=True),
        },
        operation_summary="Get room status",
    )
    @check_perms(["main.view_roomstatus"])
    def get(self, request):
        rooms = Room.objects.room_status(tenant=request.user.tenant)
        data = [room for room in rooms]
        serializer = RoomHistoryStatusSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

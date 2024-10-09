from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import RoomHistory
from main.serializers.room_status import RoomHistoryStatusSerializer


class RoomHistoryStatusView(APIView):
    @swagger_auto_schema(
        operation_description="Retrieve the status of rooms and their counts for the current tenant.",
        responses={
            200: RoomHistoryStatusSerializer(many=True),
        },
        operation_summary="Get room status",
    )
    def get(self, request):
        rooms = RoomHistory.objects.room_status(tenant=request.user.tenant)
        data = [room for room in rooms]
        serializer = RoomHistoryStatusSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

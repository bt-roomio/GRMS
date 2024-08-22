from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Room
from main.serializers.room_status import RoomStatusSerializer


class RoomStatusView(APIView):
    @swagger_auto_schema(
        operation_description="Retrieve the status of rooms and their counts for the current tenant.",
        responses={
            200: RoomStatusSerializer(many=True),
        },
        operation_summary="Get room status",
    )
    def get(self, request):
        rooms = Room.objects.room_status(tenant=request.user.tenant)
        data = [{"status": status, "count": count} for status, count in rooms]
        serializer = RoomStatusSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

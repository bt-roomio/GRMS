from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from main.models import Room
from services.serializers.room import RoomFilterSerializer, RoomSerializer
from services.swagger.room import room_list_swagger
from services.utils.permissions import DoorLockPermission


class RoomListView(APIView):
    permission_classes = (DoorLockPermission,)

    @room_list_swagger()
    def get(self, request):
        params = RoomFilterSerializer.parse(request.query_params)
        queryset = Room.objects.by_tenant(request.tenant).values("id", "number")
        serializer = RoomSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.page, params.size)
        return Response(data)

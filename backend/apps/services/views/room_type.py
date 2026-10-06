from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from main.models import RoomType
from services.serializers.room_type import RoomTypeFilterSerializer, RoomTypeSerializer
from services.swagger.room_type import room_type_list_swagger
from services.utils.permissions import DoorLockPermission


class RoomTypeListView(APIView):
    permission_classes = (DoorLockPermission,)

    @room_type_list_swagger()
    def get(self, request):
        params = RoomTypeFilterSerializer.parse(request.query_params)
        queryset = RoomType.objects.by_tenant(request.tenant).order_by(params.sort_by).values("id", "title")
        serializer = RoomTypeSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.page, params.size)
        return Response(data)

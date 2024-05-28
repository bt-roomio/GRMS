from rest_framework.views import APIView, Response

from core.utils.pagination import pagination
from main.models import RoomType
from main.serializers.room_type import RoomTypeSerializer, RoomTypeFilterParams


class RoomTypeListView(APIView):
    def get(self, request):
        params = RoomTypeFilterParams.check(request.GET)
        queryset = RoomType.objects.filter(tenant=request.user.tenant)
        serializer = RoomTypeSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))
        return Response(data)

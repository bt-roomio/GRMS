from rest_framework.views import APIView, Response

from main.models import RoomType
from main.serializers.room_type import RoomTypeSerializer


class RoomTypeListView(APIView):
    def get(self, request):
        queryset = RoomType.objects.all()
        serializer = RoomTypeSerializer(queryset, many=True)
        return Response(serializer.data)

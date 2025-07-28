from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_perms
from main.serializers.room_from_conf import RoomFromConfSerializer
from main.swagger.room_from_conf import RoomFromConfSwagger


class RoomFromConfListView(APIView):
    @swagger_auto_schema(tags=["Main, Room From Conf"], responses=RoomFromConfSwagger)
    @check_perms(["main.add_roomfromconf"])
    def post(self, request):
        serializer = RoomFromConfSerializer(data=request.data, context={"tenant": request.user.tenant})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result)

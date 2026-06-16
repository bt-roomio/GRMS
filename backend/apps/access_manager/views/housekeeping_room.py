from rest_framework.views import APIView, Response

from access_manager.serializers.housekeeping_room import HousekeepingRoomSerializer
from access_manager.swagger.housekeeping_room import housekeeping_room_swagger
from core.utils.permission import check_perms


class HousekeepingRoomView(APIView):
    @housekeeping_room_swagger()
    @check_perms(["access_manager.change_group"])
    def post(self, request):
        serializer = HousekeepingRoomSerializer(
            data=request.data,
            context={"tenant_id": request.user.tenant_id},
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result)

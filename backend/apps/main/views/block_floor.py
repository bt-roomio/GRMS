from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_perms
from main.models import Room


class BlockFloorsView(APIView):
    @swagger_auto_schema(
        tags=["Main, Block Floors"],
        operation_description="Retrieve blocks with their floors and room counts for the current tenant.",
        operation_summary="Get block floors",
    )
    @check_perms(["main.view_room"])
    def get(self, request):
        data = Room.objects.block_floors(tenant=request.user.tenant)
        return Response(data)

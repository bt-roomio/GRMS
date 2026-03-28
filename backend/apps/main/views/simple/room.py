from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_perms
from core.utils.views import TenantCachedMixin
from main.models import Room
from main.serializers.room import RoomQuickFilterParams, RoomQuickFilterParamsSwagger


class RoomQuickListView(TenantCachedMixin, APIView):
    cache_key_prefix = "rooms"

    def get_data(self, tenant_id, **kwargs):
        return list(
            Room.objects.quick_list(
                tenant=tenant_id,
                search_field=kwargs.get("search_field"),
                search_value=kwargs.get("search_value"),
            ).values("id", "number", "floor", "block")
        )

    @swagger_auto_schema(
        tags=["Main, Simple, Room"],
        query_serializer=RoomQuickFilterParamsSwagger(),
        responses={
            200: openapi.Response(
                description="Success",
                examples={
                    "application/json": [{"id": "uuid", "number": "string", "floor": "string", "block": "string"}]
                },
            )
        },
    )
    @check_perms(["main.view_room"])
    def get(self, request):
        params = RoomQuickFilterParams.check(request.GET)
        data = self.get_cached_data(str(request.user.tenant_id), **params)
        return Response(data)

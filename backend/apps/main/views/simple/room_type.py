from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_perms
from core.utils.views import TenantCachedMixin
from main.models import RoomType
from main.serializers.room_type import RoomTypeQuickFilterParams


class RoomTypeQuickListView(TenantCachedMixin, APIView):
    cache_key_prefix = "room_types"

    def get_data(self, tenant_id, **kwargs):
        return list(
            RoomType.objects.list(
                tenant=tenant_id,
                search_field=kwargs.get("search_field"),
                search_value=kwargs.get("search_value"),
            ).values("id", "title")
        )

    @swagger_auto_schema(
        tags=["Main, Simple, Room Type"],
        query_serializer=RoomTypeQuickFilterParams(),
        responses={200: openapi.Response(description="Success", examples={"application/json": [{"id": "uuid", "title": "string"}]})},
    )
    @check_perms(["main.view_roomtype"])
    def get(self, request):
        params = RoomTypeQuickFilterParams.check(request.GET)
        data = self.get_cached_data(str(request.user.tenant_id), **params)
        return Response(data)

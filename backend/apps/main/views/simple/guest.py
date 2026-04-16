from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_perms
from core.utils.views import TenantCachedMixin
from main.models import Guest
from main.serializers.guest import GuestQuickFilterParams


class GuestQuickListView(TenantCachedMixin, APIView):
    cache_key_prefix = "guests"

    def get_data(self, tenant_id, **kwargs):
        return list(
            Guest.objects.quick_list(
                tenant_id=tenant_id,
                search_value=kwargs.get("search_value"),
                room=kwargs.get("room"),
            ).values("id", "name", "lastname", "room_id")
        )

    @swagger_auto_schema(
        tags=["Main, Simple"],
        query_serializer=GuestQuickFilterParams(),
        responses={
            200: openapi.Response(
                description="Success",
                examples={"application/json": [{"id": "uuid", "name": "string", "lastname": "string"}]},
            )
        },
    )
    @check_perms(["main.view_guest"])
    def get(self, request):
        params = GuestQuickFilterParams.check(request.GET)
        data = self.get_cached_data(str(request.user.tenant_id), **params)
        return Response(data)

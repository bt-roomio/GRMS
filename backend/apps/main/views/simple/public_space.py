from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_perms
from core.utils.views import TenantCachedMixin
from main.models import PublicSpace
from main.serializers.public_space import PublicSpaceQuickFilterParams


class PublicSpaceQuickListView(TenantCachedMixin, APIView):
    cache_key_prefix = "public_spaces"

    def get_data(self, tenant_id, **kwargs):
        return list(
            PublicSpace.objects.quick_list(
                tenant_id=tenant_id,
                search_value=kwargs.get("search_value"),
            ).values("id", "name")
        )

    @swagger_auto_schema(
        tags=["Main, Simple"],
        query_serializer=PublicSpaceQuickFilterParams(),
        responses={
            200: openapi.Response(
                description="Success", examples={"application/json": [{"id": "uuid", "name": "string"}]}
            )
        },
    )
    @check_perms(["main.view_publicspace"])
    def get(self, request):
        params = PublicSpaceQuickFilterParams.check(request.GET)
        data = self.get_cached_data(str(request.user.tenant_id), **params)
        return Response(data)

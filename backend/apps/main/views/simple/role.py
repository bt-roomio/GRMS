from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_perms
from core.utils.views import TenantCachedMixin
from users.models import Role
from users.serializers.role import RoleQuickFilterParams


class RoleQuickListView(TenantCachedMixin, APIView):
    cache_key_prefix = "roles"

    def get_data(self, tenant_id, **kwargs):
        return list(
            Role.objects.quick_list(tenant=tenant_id, search_value=kwargs.get("search_value")).values("id", "name")
        )

    @swagger_auto_schema(
        tags=["Main, Simple"],
        query_serializer=RoleQuickFilterParams(),
        responses={
            200: openapi.Response(
                description="Success", examples={"application/json": [{"id": "uuid", "name": "string"}]}
            )
        },
    )
    @check_perms(["users.view_role"])
    def get(self, request):
        params = RoleQuickFilterParams.check(request.GET)
        data = self.get_cached_data(str(request.user.tenant_id), **params)
        return Response(data)

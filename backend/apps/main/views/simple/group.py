from access_manager.models import Group
from access_manager.serializers.group import GroupQuickFilterParams

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_perms
from core.utils.views import TenantCachedMixin


class GroupQuickListView(TenantCachedMixin, APIView):
    cache_key_prefix = "groups"

    def get_data(self, tenant_id, **kwargs):
        query = Group.objects.quick_list(
            tenant_id=tenant_id,
            search_value=kwargs.get("search_value"),
        ).values("id", "name")
        return list(query)

    @swagger_auto_schema(
        tags=["Main, Simple"],
        query_serializer=GroupQuickFilterParams(),
        responses={
            200: openapi.Response(
                description="Success", examples={"application/json": [{"id": "uuid", "name": "string"}]}
            )
        },
    )
    @check_perms(["auth.view_group"])
    def get(self, request):
        params = GroupQuickFilterParams.check(request.GET)
        data = self.get_cached_data(str(request.user.tenant_id), **params)
        return Response(data)

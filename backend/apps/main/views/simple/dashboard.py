from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_perms
from core.utils.views import TenantCachedMixin
from main.models import Dashboard
from main.serializers.dashboard import DashboardQuickFilterParams


class DashboardQuickListView(TenantCachedMixin, APIView):
    cache_key_prefix = "dashboards"

    def get_data(self, tenant_id, **kwargs):
        return list(
            Dashboard.objects.quick_list(
                tenant_id=tenant_id,
                search_value=kwargs.get("search_value"),
            ).values("id", "title")
        )

    @swagger_auto_schema(
        tags=["Main, Simple, Dashboard"],
        query_serializer=DashboardQuickFilterParams(),
        responses={200: openapi.Response(description="Success", examples={"application/json": [{"id": "uuid", "title": "string"}]})},
    )
    @check_perms(["main.view_dashboard"])
    def get(self, request):
        params = DashboardQuickFilterParams.check(request.GET)
        data = self.get_cached_data(str(request.user.tenant_id), **params)
        return Response(data)

from admin_panel.swagger.tenants import AdminTenantListSwagger

from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import IsSuperUser
from main.models import Tenant
from main.serializers.tenant import TenantFilterParams, TenantSerializer


class AdminTenantListView(APIView):
    permission_classes = (IsSuperUser,)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses=AdminTenantListSwagger,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Returns a list of all tenants.",
    )
    def get(self, request):
        params = TenantFilterParams.check(request.query_params)
        queryset = Tenant.objects.list(
            sort_by=params.get("sort_by"),
            search_field=params.get("search_field"),
            search_value=params.get("search_value"),
        )
        serializer = TenantSerializer(queryset, many=True)
        return Response(serializer.data)

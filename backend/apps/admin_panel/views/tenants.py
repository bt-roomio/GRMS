from admin_panel.swagger.tenants import AdminTenantCreateSwagger, AdminTenantListSwagger

from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import IsSuperUser
from main.models import Tenant
from main.serializers.tenant import CreateTenantSerializer, TenantFilterParams, TenantSerializer


class AdminTenantListView(APIView):
    permission_classes = (IsSuperUser,)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses=AdminTenantListSwagger,
        query_serializer=TenantFilterParams,
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

    @swagger_auto_schema(
        tags=["Admin Panel"],
        request_body=CreateTenantSerializer,
        responses=AdminTenantCreateSwagger,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Creates a new tenant with an admin user and default device profiles.",
    )
    def post(self, request):
        serializer = CreateTenantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer = serializer.save()
        data = TenantSerializer(serializer).data
        return Response(data, 201)

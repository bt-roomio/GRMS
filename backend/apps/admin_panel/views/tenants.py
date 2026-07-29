from admin_panel.swagger.tenants import (
    AdminTenantCreateSwagger,
    AdminTenantDetailSwagger,
    AdminTenantListSwagger,
    AdminTenantUpdateSwagger,
)
from django.db.models import Prefetch
from django.http import Http404

from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import IsSuperUser
from main.models import Device, Tenant
from main.serializers.tenant import CreateTenantSerializer, TenantFilterParams, TenantSerializer, UpdateTenantSerializer


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
        queryset = Tenant.objects.list(  # ty: ignore
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


class AdminTenantDetailView(APIView):
    permission_classes = (IsSuperUser,)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses=AdminTenantDetailSwagger,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Returns detailed information about a specific tenant.",
    )
    def get(self, _, tenant_id):
        gateways = Device.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
            additional_info__gateway=True,
        )
        tenant: Tenant | None = (
            Tenant.objects.filter(id=tenant_id)  # ty: ignore
            .prefetch_related(Prefetch("device_set", gateways, "gateways"))
            .count_devices()
            .first()
        )
        if not tenant:
            raise Http404("No Tenant matches the given query.")
        serializer = TenantSerializer(tenant)
        return Response(serializer.data)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        request_body=UpdateTenantSerializer,
        responses=AdminTenantUpdateSwagger,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Updates data for a specific tenant.",
    )
    def put(self, request, tenant_id):
        gateways = Device.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
            additional_info__gateway=True,
        )
        tenant: Tenant | None = (
            Tenant.objects.filter(id=tenant_id)  # ty: ignore
            .prefetch_related(Prefetch("device_set", gateways, "gateways"))
            .count_devices()
            .first()
        )
        if not tenant:
            raise Http404("No Tenant matches the given query.")
        serializer = UpdateTenantSerializer(tenant, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TenantSerializer(tenant).data)

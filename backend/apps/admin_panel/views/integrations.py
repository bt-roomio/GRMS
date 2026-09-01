from admin_panel.serializers.integrations import (
    CreateIntegrationSerializer,
    IntegrationSerializer,
    IntegrationToggleSerializer,
)
from admin_panel.swagger.integrations import (
    AdminTenantIntegrationCreateSwagger,
    AdminTenantIntegrationDetailSwagger,
    AdminTenantIntegrationsSwagger,
    AdminTenantIntegrationToggleSwagger,
)
from admin_panel.utils.scope import get_scoped_tenant_or_404

from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import IsSuperUser
from services.models import Integration


class AdminTenantIntegrationsView(APIView):
    permission_classes = (IsSuperUser,)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses=AdminTenantIntegrationsSwagger,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Returns every integration of the tenant, enabled or not.",
    )
    def get(self, request, tenant_id):
        tenant = get_scoped_tenant_or_404(request, tenant_id)
        queryset = Integration.objects.filter(tenant=tenant, is_active=True).select_related("integrator")
        data = IntegrationSerializer(queryset, many=True).data
        return Response(data)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        request_body=CreateIntegrationSerializer,
        responses=AdminTenantIntegrationCreateSwagger,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Creates an integration for the tenant.",
    )
    def post(self, request, tenant_id):
        tenant = get_scoped_tenant_or_404(request, tenant_id)
        serializer = CreateIntegrationSerializer(data=request.data, context={"tenant": tenant})
        serializer.is_valid(raise_exception=True)
        integration = serializer.save(tenant=tenant, created_by=request.user)
        return Response(IntegrationSerializer(integration).data, 201)


class AdminTenantIntegrationDetailView(APIView):
    permission_classes = (IsSuperUser,)

    def get_integration(self, request, tenant_id, integrator):
        """404 for a tenant outside the caller's scope, courtesy of get_scoped_tenant_or_404."""
        tenant = get_scoped_tenant_or_404(request, tenant_id)
        return get_object_or_404(
            Integration.objects.select_related("integrator"),
            tenant=tenant,
            integrator__name__iexact=integrator,
            is_active=True,
        )

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses=AdminTenantIntegrationDetailSwagger,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Returns one integration of the tenant.",
    )
    def get(self, request, tenant_id, integrator):
        instance = self.get_integration(request, tenant_id, integrator)
        return Response(IntegrationSerializer(instance).data)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        request_body=IntegrationToggleSerializer,
        responses=AdminTenantIntegrationToggleSwagger,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Turns the tenant's integration on or off.",
    )
    def patch(self, request, tenant_id, integrator):
        instance = self.get_integration(request, tenant_id, integrator)
        # Not partial: the serializer holds a single field, and `enable` is the whole point of the call.
        serializer = IntegrationToggleSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(IntegrationSerializer(instance).data)

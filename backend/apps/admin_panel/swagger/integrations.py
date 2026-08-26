from admin_panel.serializers.integrations import IntegrationSerializer

from drf_yasg import openapi

AdminTenantIntegrationsSwagger = {
    200: openapi.Response(description="Success", schema=IntegrationSerializer(many=True)),
    404: openapi.Response(description="Tenant not found"),
}

AdminTenantIntegrationCreateSwagger = {
    201: openapi.Response(description="Created", schema=IntegrationSerializer),
    400: openapi.Response(description="Invalid data"),
    404: openapi.Response(description="Tenant not found"),
}

AdminTenantIntegrationDetailSwagger = {
    200: openapi.Response(description="Success", schema=IntegrationSerializer),
    404: openapi.Response(description="Tenant or integration not found"),
}

AdminTenantIntegrationToggleSwagger = {
    200: openapi.Response(description="Success", schema=IntegrationSerializer),
    400: openapi.Response(description="Invalid data"),
    404: openapi.Response(description="Tenant or integration not found"),
}

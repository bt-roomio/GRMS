from drf_yasg import openapi

from main.serializers.tenant import TenantSerializer

AdminTenantListSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": {"count": "Count of data.", "results": "Array of data."}},
        schema=TenantSerializer,
    ),
}

AdminTenantCreateSwagger = {
    201: openapi.Response(
        description="Tenant created",
        schema=TenantSerializer,
    ),
    400: openapi.Response(description="Validation error"),
}

AdminTenantDetailSwagger = {
    200: openapi.Response(
        description="Success",
        schema=TenantSerializer,
    ),
    404: openapi.Response(description="Tenant not found"),
}

AdminTenantUpdateSwagger = {
    200: openapi.Response(
        description="Tenant updated",
        schema=TenantSerializer,
    ),
    400: openapi.Response(description="Validation error"),
    404: openapi.Response(description="Tenant not found"),
}

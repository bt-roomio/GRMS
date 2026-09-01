from drf_yasg import openapi

from main.serializers.tenant_group import TenantGroupSerializer

_EXAMPLE = {
    "id": "3f2b8c14-0f1a-4a7e-9a3f-5c9d2e7b1a44",
    "title": "Hilton Uzbekistan",
    "description": "Hotel chain",
    "is_active": True,
    "additional_info": None,
    "tenants_count": 2,
}

AdminTenantGroupListSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": {"count": 1, "results": [_EXAMPLE]}},
        schema=TenantGroupSerializer(many=True),
    ),
}

AdminTenantGroupCreateSwagger = {
    201: openapi.Response(
        description="Created together with its chain admin",
        examples={"application/json": _EXAMPLE},
    ),
    400: openapi.Response(description="Validation error"),
}

AdminTenantGroupDetailSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": _EXAMPLE},
        schema=TenantGroupSerializer,
    ),
    404: openapi.Response(description="Tenant group not found"),
}

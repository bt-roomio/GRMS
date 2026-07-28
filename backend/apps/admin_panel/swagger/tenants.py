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

_GATEWAY_EXAMPLE = {
    "id": "b3b1c2e4-1234-4a5b-8c6d-000000000001",
    "name": "Gateway 1",
    "status": True,
    "is_gateway": True,
    "excluded_monitoring": False,
}

_TENANT_DETAIL_EXAMPLE = {
    "id": "b3b1c2e4-1234-4a5b-8c6d-000000000000",
    "created_at": "2024-01-01T00:00:00Z",
    "title": "Hotel Example",
    "email": "admin@example.com",
    "tenant_profile": "b3b1c2e4-1234-4a5b-8c6d-000000000002",
    "additional_info": {},
    "address": "",
    "address2": "",
    "city": "",
    "country": "",
    "phone": "",
    "region": "",
    "state": "",
    "zip": "",
    "online_rooms": 12,
    "offline_rooms": 3,
    "total_rooms": 15,
    "offline_gateways": 1,
    "total_gateways": 4,
    "gateways": [_GATEWAY_EXAMPLE],
}

AdminTenantDetailSwagger = {
    200: openapi.Response(
        description="Success. Includes computed room/gateway counts and the tenant's `gateways` list "
        "(each with `id`, `name`, `status`, `is_gateway`, `excluded_monitoring`).",
        examples={"application/json": _TENANT_DETAIL_EXAMPLE},
        schema=TenantSerializer,
    ),
    404: openapi.Response(description="Tenant not found"),
}

AdminTenantUpdateSwagger = {
    200: openapi.Response(
        description="Tenant updated. To toggle monitoring exclusion for specific gateways, pass "
        '`gateways: [{"id": ..., "excluded_monitoring": true}]` in the request body; other fields '
        "are optional (partial update).",
        examples={"application/json": _TENANT_DETAIL_EXAMPLE},
        schema=TenantSerializer,
    ),
    400: openapi.Response(description="Validation error"),
    404: openapi.Response(description="Tenant not found"),
}

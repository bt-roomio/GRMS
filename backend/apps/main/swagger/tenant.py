from drf_yasg import openapi

from main.serializers.tenant import TenantSerializer

TenantSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": {"count": "Count of data.", "results": "Array of data."}},
        schema=TenantSerializer,
    ),
}

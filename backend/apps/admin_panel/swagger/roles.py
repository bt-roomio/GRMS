from drf_yasg import openapi

from users.serializers.role import RoleSimpleSerializer

AdminTenantRolesSwagger = {
    200: openapi.Response(
        description="Success",
        schema=RoleSimpleSerializer,
    ),
    404: openapi.Response(description="Tenant not found"),
}

from drf_yasg import openapi

from users.serializers.user import UserSerializer

AdminTenantUsersSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": {"count": "Count of data.", "results": "Array of data."}},
        schema=UserSerializer,
    ),
}

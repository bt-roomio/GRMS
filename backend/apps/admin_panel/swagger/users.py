from drf_yasg import openapi

from users.serializers.user import UserSerializer

AdminTenantUsersSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": {"count": "Count of data.", "results": "Array of data."}},
        schema=UserSerializer,
    ),
}

AdminCreateTenantUserSwagger = {
    201: openapi.Response(
        description="User created",
        examples={
            "application/json": {
                "user": "User data object",
                "activation_link": "https://example.com/password/new/?key=...",
            }
        },
    ),
    400: openapi.Response(description="Validation error"),
}

AdminTenantUserDetailSwagger = {
    200: openapi.Response(
        description="Success",
        schema=UserSerializer,
    ),
    404: openapi.Response(description="User not found"),
}

AdminChangePasswordSwagger = {
    200: openapi.Response(
        description="Password changed",
        examples={"application/json": {"message": "Password changed."}},
    ),
    400: openapi.Response(description="Validation error"),
    404: openapi.Response(description="User not found"),
}

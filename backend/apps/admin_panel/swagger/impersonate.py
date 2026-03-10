from drf_yasg import openapi

ImpersonateSwagger = {
    200: openapi.Response(
        description="Success",
        examples={
            "application/json": {
                "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        },
        schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "access": openapi.Schema(type=openapi.TYPE_STRING, description="JWT access token"),
                "refresh": openapi.Schema(type=openapi.TYPE_STRING, description="JWT refresh token"),
            },
        ),
    ),
    404: openapi.Response(description="User not found or inactive"),
}

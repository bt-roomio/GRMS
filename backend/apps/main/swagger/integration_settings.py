from drf_yasg import openapi

IntegrationSettingsSwagger = {
    400: openapi.Response(
        description="Bad request",
        examples={
            "application/json": {
                "detail": [
                    "Authentication credentials were not provided.",
                    "Given token not valid for any token type",
                ]
            }
        },
    ),
}

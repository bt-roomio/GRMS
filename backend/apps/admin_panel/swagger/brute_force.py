from drf_yasg import openapi

AdminUnlockUserSwagger = {
    200: openapi.Response(
        description="Account unlocked",
        examples={
            "application/json": {
                "message": "Account unlocked.",
                "email": "user@example.com",
                "cleared_ips": ["203.0.113.10"],
                "cleared_keys": 18,
            }
        },
    ),
    403: openapi.Response(description="No `main.unlock_user` permission"),
    404: openapi.Response(description="User not found"),
}

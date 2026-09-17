from drf_yasg import openapi

AdminUserLockStatusSwagger = {
    200: openapi.Response(
        description="Lock status",
        examples={
            "application/json": {
                "email": "user@example.com",
                "is_locked": True,
                "known_ips": ["203.0.113.10"],
                "locks": [
                    {
                        "ip": "203.0.113.10",
                        "endpoint": "/api/v1/users/access-token/",
                        "reason": "lockout",
                        "seconds_left": 742,
                    }
                ],
            }
        },
    ),
    404: openapi.Response(description="User not found"),
}

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
    404: openapi.Response(description="User not found"),
}

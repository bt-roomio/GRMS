from drf_yasg import openapi

EmailConfigSwagger = {
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

EmailConfigUpdateSwagger = {
    400: openapi.Response(
        description="Bad request",
        examples={
            "application/json": {
                "detail": [
                    "Authentication credentials were not provided.",
                    "Given token not valid for any token type",
                ],
                "email": [
                    "This field is required.",
                    "There is not user with this email.",
                    "Enter a valid email address.",
                    "This field may not be blank.",
                ],
            }
        },
    ),
}

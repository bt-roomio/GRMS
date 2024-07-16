from drf_yasg import openapi

ActivationLinkSwagger = {
    200: openapi.Response(
        description="Return FRONTEND_DOMAIN and activation link or send email with activation link.",
        examples={"str": ""},
    ),
}

ResetPasswordSwagger = {
    400: openapi.Response(
        description="Bad request",
        examples={
            "application/json": {
                "key": ["This field is required.", "This field may not be blank."],
                "new_password": [
                    "Same as in key.",
                    "Password must be at least 8 characters long with at least one capital letter and symbol",
                ],
                "confirm_password": ["Same as in key."],
                "detail": "No ResetPassword matches the given query.",
            }
        },
    ),
}

from drf_yasg import openapi

ResetLinkSwagger = {
    400: openapi.Response(
        description="Bad request",
        examples={"application/json": {
            'email': [
                'This field is required.',
                'There is not user with this email.',
                'Enter a valid email address.',
                'This field may not be blank.'],
        }}
    ),
}

ResetPasswordSwagger = {
    400: openapi.Response(
        description="Bad request",
        examples={"application/json": {
            "key": ["This field is required.", "This field may not be blank."],
            "new_password": ["Same as in key.",
                             "Password must be at least 8 characters long with at least one capital letter and symbol"],
            "confirm_password": ["Same as in key."],
            "detail": "No ResetPassword matches the given query.",
        }}
    ),
}

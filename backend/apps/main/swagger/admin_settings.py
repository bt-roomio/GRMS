from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from main.serializers.admin_settings import AdminSettingsSerializer


def admin_settings_swagger():
    return swagger_auto_schema(
        responses={
            200: AdminSettingsSerializer(),
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
        },
        tags=["Main, Admin Settings"],
    )

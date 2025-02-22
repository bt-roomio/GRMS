from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from main.serializers.alarm_settings import AlarmSettingsSerializer

AlarmSettingsSwagger = {
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
    200: openapi.Response(
        description="Alarm settings",
        schema=AlarmSettingsSerializer,
    ),
}


def alarm_settings_swagger():
    return swagger_auto_schema(
        query_serializer=AlarmSettingsSerializer,
        responses={
            200: AlarmSettingsSerializer(),
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
        tags=["Main, Alarm Settings"],
    )

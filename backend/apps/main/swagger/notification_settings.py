from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from main.serializers.notification_settings import NotificationSettingsSerializer

BAD_REQUEST = openapi.Response(
    description="Bad request",
    examples={"application/json": {"detail": ["Authentication credentials were not provided."]}},
)

TAG = "Main, Notification Settings"


def notification_settings_swagger():
    return swagger_auto_schema(
        responses={200: NotificationSettingsSerializer(), 400: BAD_REQUEST},
        tags=[TAG],
    )


def notification_settings_update_swagger():
    return swagger_auto_schema(
        request_body=NotificationSettingsSerializer,
        responses={200: NotificationSettingsSerializer(), 400: BAD_REQUEST},
        tags=[TAG],
    )

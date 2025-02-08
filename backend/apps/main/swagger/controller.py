from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def swagger():
    return swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "device_id",
                openapi.IN_PATH,
                description="UUID of the device",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
            ),
            openapi.Parameter("name", openapi.IN_PATH, description="Name of the attribute", type=openapi.TYPE_STRING),
        ],
        responses={
            200: "List of controllers.",
            400: '{"detail": "Error message!"}',
        },
    )

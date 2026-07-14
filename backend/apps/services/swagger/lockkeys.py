from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from services.serializers.lockkeys import RoomLockKeySerializer

_auth_error_response = openapi.Response(
    description="Authentication credentials were not provided or are invalid.",
    examples={"application/json": {"detail": "Authentication credentials were not provided."}},
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={"detail": openapi.Schema(type=openapi.TYPE_STRING)},
    ),
)

_timeout_response = openapi.Response(
    description="Device did not respond within the timeout period (10 seconds).",
    examples={
        "application/json": {
            "device": "38:0c:6e:41:02:80",
            "data": {"success": False, "msg": "Timeout error"},
        }
    },
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "device": openapi.Schema(type=openapi.TYPE_STRING, description="Device MAC address"),
            "data": openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    "msg": openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
        },
    ),
)


def lockkeys_doors_list_swagger(**kwargs):
    return swagger_auto_schema(
        operation_summary="List Lock Key Doors",
        operation_description="Retrieve a list of all rooms and public spaces with door lock devices.",
        responses={
            200: RoomLockKeySerializer(many=True),
            401: _auth_error_response,
        },
        tags=["Services, Lock Keys"],
    )


def lockkeys_door_open_swagger(**kwargs):
    return swagger_auto_schema(
        operation_summary="Open Door",
        operation_description=(
            "Send an unlock command to the specified door lock device. "
            "If the device does not respond within 10 seconds, a timeout error is returned with HTTP 200."
        ),
        responses={
            200: openapi.Response(
                description="Success response or timeout error (both returned as HTTP 200).",
                examples={
                    "application/json (success)": {
                        "device": "38:0c:6e:41:02:80",
                        "data": {"success": True},
                    },
                    "application/json (timeout)": {
                        "device": "38:0c:6e:41:02:80",
                        "data": {"success": False, "msg": "Timeout error"},
                    },
                },
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "device": openapi.Schema(type=openapi.TYPE_STRING, description="Device MAC address"),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                "msg": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    description='Present only on timeout: "Timeout error"',
                                ),
                            },
                        ),
                    },
                ),
            ),
            401: _auth_error_response,
            404: openapi.Response(description="Device not found."),
        },
        tags=["Services, Lock Keys"],
    )

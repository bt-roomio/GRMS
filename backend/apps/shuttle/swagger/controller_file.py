from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from shuttle.serializers.controller_file import ControllerParams

_TAG = "Shuttle, Controller File"

_controller_list_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "count": openapi.Schema(type=openapi.TYPE_INTEGER),
        "total_pages": openapi.Schema(type=openapi.TYPE_INTEGER),
        "results": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "id": openapi.Schema(type=openapi.TYPE_STRING, format="uuid"),
                    "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                    "mac_address": openapi.Schema(type=openapi.TYPE_STRING),
                    "tenant": openapi.Schema(type=openapi.TYPE_STRING, format="uuid"),
                    "file_type": openapi.Schema(type=openapi.TYPE_STRING),
                    "file_path": openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
        ),
    },
)

_controller_file_request = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "controllers": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_STRING),
            description="List of mac addresses. Example: ['11:22:33:44:55:66']",
        ),
        "file": openapi.Schema(
            type=openapi.TYPE_FILE,
            description="Upload file (Firmware, Boot-Defaults, Config, Site-File).",
        ),
        "file_type": openapi.Schema(type=openapi.TYPE_STRING, description="Type of file"),
    },
)


def controller_list_swagger():
    return swagger_auto_schema(
        tags=[_TAG],
        query_serializer=ControllerParams(),
        responses={200: _controller_list_response},
        operation_description="Returns a paginated list of controllers with their associated file info.",
    )


def controller_file_swagger():
    return swagger_auto_schema(
        tags=[_TAG],
        request_body=_controller_file_request,
        responses={200: "Upload successful."},
        operation_description="Upload a firmware or config file and assign it to one or more controllers by mac address.",
    )

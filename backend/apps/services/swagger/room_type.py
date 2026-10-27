from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from services.serializers.room_type import RoomTypeFilterSerializer

_auth_error_response = openapi.Response(
    description="Authentication credentials were not provided or are invalid.",
    examples={"application/json": {"detail": "Authentication credentials were not provided."}},
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={"detail": openapi.Schema(type=openapi.TYPE_STRING)},
    ),
)

_room_type_list_response = openapi.Response(
    description="Paginated list of room types for the current tenant.",
    examples={
        "application/json": {
            "count": 42,
            "results": [
                {"id": "0f6c1d2e-3a4b-4c5d-8e9f-1a2b3c4d5e6f", "title": "Standard"},
                {"id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d", "title": "Deluxe"},
            ],
        }
    },
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "count": openapi.Schema(type=openapi.TYPE_INTEGER, description="Total number of room types."),
            "results": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                        "title": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    ),
)


def room_type_list_swagger(**kwargs):
    return swagger_auto_schema(
        operation_summary="List Room Types",
        operation_description=(
            "Retrieve a paginated list of active room types for the current tenant. "
            "Supports pagination via `page`/`size` and ordering via `sort_by`."
        ),
        query_serializer=RoomTypeFilterSerializer,
        responses={
            200: _room_type_list_response,
            401: _auth_error_response,
        },
        tags=["Services, Room Types"],
    )

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from services.serializers.room import RoomFilterSerializer

_auth_error_response = openapi.Response(
    description="Authentication credentials were not provided or are invalid.",
    examples={"application/json": {"detail": "Authentication credentials were not provided."}},
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={"detail": openapi.Schema(type=openapi.TYPE_STRING)},
    ),
)

_room_list_response = openapi.Response(
    description="Paginated list of rooms for the current tenant.",
    examples={
        "application/json": {
            "count": 42,
            "results": [
                {
                    "id": "0f6c1d2e-3a4b-4c5d-8e9f-1a2b3c4d5e6f",
                    "number": "101",
                    "type_id": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e",
                    "type_name": "Standard",
                },
                {
                    "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
                    "number": "102",
                    "type_id": None,
                    "type_name": None,
                },
            ],
        }
    },
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "count": openapi.Schema(type=openapi.TYPE_INTEGER, description="Total number of rooms."),
            "results": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                        "number": openapi.Schema(type=openapi.TYPE_STRING),
                        "type_id": openapi.Schema(
                            type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID, x_nullable=True
                        ),
                        "type_name": openapi.Schema(type=openapi.TYPE_STRING, x_nullable=True),
                    },
                ),
            ),
        },
    ),
)


def room_list_swagger(**kwargs):
    return swagger_auto_schema(
        operation_summary="List Rooms",
        operation_description=(
            "Retrieve a paginated list of rooms for the current tenant. "
            "Supports pagination via `page`/`size` and ordering via `sort_by`."
        ),
        query_serializer=RoomFilterSerializer,
        responses={
            200: _room_list_response,
            401: _auth_error_response,
        },
        tags=["Services, Rooms"],
    )

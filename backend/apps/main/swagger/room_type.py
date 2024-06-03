from drf_yasg import openapi

from main.serializers.room_type import RoomTypeSerializer

RoomTypeSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": {"count": "Count of data.", "results": "Array of data."}},
    ),
}

RoomTypeDetailSwagger = {200: RoomTypeSerializer}

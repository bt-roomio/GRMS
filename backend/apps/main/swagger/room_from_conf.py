from drf_yasg import openapi

from main.serializers.room_from_conf import RoomFromConfSerializer

RoomFromConfSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": {"count": "Count of data.", "results": "Array of data."}},
        schema=RoomFromConfSerializer,
    ),
}

RoomFromConfDetailSwagger = {200: RoomFromConfSerializer}

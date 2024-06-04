from drf_yasg import openapi
from main.serializers.room import RoomSerializer

RoomSwagger = {
	200: openapi.Response(
		description="Success",
		examples={"application/json": {"count": "Count of data.", "results": "Array of data."}},
		schema=RoomSerializer,
	),
}

RoomDetailSwagger = {200: RoomSerializer}

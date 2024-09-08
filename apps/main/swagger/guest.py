from drf_yasg import openapi

from main.serializers.guest import GuestSerializer

GuestSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": {"count": "Count of data.", "results": "Array of data."}},
        schema=GuestSerializer,
    ),
}

GuestDetailSwagger = {200: GuestSerializer}

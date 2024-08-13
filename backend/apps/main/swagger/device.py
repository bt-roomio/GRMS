from drf_yasg import openapi

from main.serializers.device import DeviceSerializer

DeviceSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": {"count": "Count of data.", "results": "Array of data."}},
        schema=DeviceSerializer,
    ),
}

DeviceDetailSwagger = {200: DeviceSerializer}

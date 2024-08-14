from drf_yasg import openapi

from main.serializers.device_profile import DeviceProfileSerializer

DeviceProfileSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": {"count": "Count of data.", "results": "Array of data."}},
        schema=DeviceProfileSerializer,
    ),
}

DeviceProfileDetailSwagger = {200: DeviceProfileSerializer}

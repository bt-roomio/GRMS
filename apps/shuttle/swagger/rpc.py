from drf_yasg import openapi

RPCSwagger = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "device": openapi.Schema(type=openapi.TYPE_STRING, description="Device name"),
        "id": openapi.Schema(type=openapi.TYPE_STRING, description="Message ID"),
        "data": openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description="Response data (optional)",
            properties={"success": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Success")},
        ),
    },
)

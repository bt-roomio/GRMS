from drf_yasg import openapi

ControllerFileSwagger = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "content": openapi.Schema(
            type=openapi.TYPE_FILE, description="Upload (Firmware, Boot-Defaults, Config, Site-File) file."
        ),
    },
)

ControllerFileResponseSwagger = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "content": openapi.Schema(type=openapi.TYPE_STRING, description="Path of file"),
        "id": openapi.Schema(type=openapi.TYPE_STRING, description="UUID of file"),
    },
)

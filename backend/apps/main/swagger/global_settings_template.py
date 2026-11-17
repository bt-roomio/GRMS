from drf_yasg import openapi

from main.serializers.global_settings_template import (
    ApplyGlobalSettingsTemplateResponseSerializer,
    GlobalSettingsRoomSerializer,
    GlobalSettingsTemplateSerializer,
)

_EXAMPLE = {
    "id": "9b0c7e2a-5d41-4f6e-8a3b-1c2d3e4f5a6b",
    "name": "Default hotel",
    "config": {"timezone": 5, "guest_auto_block": True},
    "used": 0,
    "config_updated_at": "2026-11-16T10:00:00Z",
    "created_at": "2026-11-16T10:00:00Z",
    "updated_at": "2026-11-16T10:00:00Z",
}

GlobalSettingsTemplateListSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": {"count": 1, "results": [_EXAMPLE]}},
        schema=GlobalSettingsTemplateSerializer(many=True),
    ),
}

GlobalSettingsTemplateCreateSwagger = {
    201: openapi.Response(description="Created", examples={"application/json": _EXAMPLE}),
    400: openapi.Response(description="Validation error"),
}

GlobalSettingsTemplateDetailSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": _EXAMPLE},
        schema=GlobalSettingsTemplateSerializer,
    ),
    404: openapi.Response(description="Global settings template not found"),
}

_ROOM_EXAMPLE = {
    "id": "5e1f2a3b-4c5d-4e6f-8a9b-0c1d2e3f4a5b",
    "number": "101",
    "floor": "1",
    "block": "A",
    "room_type": {"id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d", "title": "Standard"},
    "device": {"id": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e", "name": "RCU-101"},
    "template": {"id": "9b0c7e2a-5d41-4f6e-8a3b-1c2d3e4f5a6b", "name": "Default hotel", "status": "up_to_date"},
}

GlobalSettingsRoomListSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": [_ROOM_EXAMPLE]},
        schema=GlobalSettingsRoomSerializer(many=True),
    ),
    400: openapi.Response(description="Validation error"),
}

ApplyGlobalSettingsTemplateSwagger = {
    200: openapi.Response(
        description="Ids of the devices the template was applied to",
        examples={"application/json": {"devices": ["2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e"]}},
        schema=ApplyGlobalSettingsTemplateResponseSerializer,
    ),
    400: openapi.Response(description="Validation error: unknown rooms or template"),
}

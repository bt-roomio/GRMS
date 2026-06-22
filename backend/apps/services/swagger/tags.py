from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

_auth_error_response = openapi.Response(
    description="Authentication credentials were not provided or are invalid.",
    examples={"application/json": {"detail": "Authentication credentials were not provided."}},
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={"detail": openapi.Schema(type=openapi.TYPE_STRING)},
    ),
)

_tags_list_response = openapi.Response(
    description="Room info with its CLIENT_SCOPE attributes and latest telemetry.",
    examples={
        "application/json": {
            "room": {"id": "0f6c1d2e-3a4b-4c5d-8e9f-1a2b3c4d5e6f", "number": "101"},
            "attributes": [
                {
                    "device": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
                    "key_name": "targetTemperature",
                    "last_update_ts": 1718000000000,
                    "value": 22.5,
                }
            ],
            "telemetry": [
                {
                    "device": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
                    "key_name": "temperature",
                    "value": 21.8,
                    "ts": 1718000000000,
                }
            ],
        }
    },
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "room": openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                    "number": openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
            "attributes": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "device": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                        "key_name": openapi.Schema(type=openapi.TYPE_STRING),
                        "last_update_ts": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "value": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            "telemetry": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "device": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                        "key_name": openapi.Schema(type=openapi.TYPE_STRING),
                        "value": openapi.Schema(type=openapi.TYPE_STRING),
                        "ts": openapi.Schema(type=openapi.TYPE_INTEGER),
                    },
                ),
            ),
        },
    ),
)


_tag_object_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
        "device": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
        "key_name": openapi.Schema(type=openapi.TYPE_STRING),
        "type": openapi.Schema(type=openapi.TYPE_STRING, enum=["ATTRIBUTE", "TELEMETRY"]),
        "last_update_ts": openapi.Schema(type=openapi.TYPE_INTEGER),
        "value": openapi.Schema(type=openapi.TYPE_STRING),
    },
)


def tag_detail_get_swagger(**kwargs):
    return swagger_auto_schema(
        operation_summary="Retrieve Tag",
        operation_description=(
            "Retrieve a single tag by its id. A tag is backed by either an attribute "
            "(type=ATTRIBUTE) or latest telemetry (type=TELEMETRY)."
        ),
        responses={
            200: openapi.Response(description="Tag.", schema=_tag_object_schema),
            401: _auth_error_response,
            404: openapi.Response(description="Tag not found for the current tenant."),
        },
        tags=["Services, Tags"],
    )


def tag_detail_put_swagger(**kwargs):
    return swagger_auto_schema(
        operation_summary="Update Tag Value",
        operation_description=(
            "Update the tag value (persisted to the type-compatible column) and push the new value "
            "to the device via MQTT RPC: setAttribute for attributes, setTelemetry for telemetry."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["value"],
            properties={
                "value": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="New tag value; any JSON scalar/object, routed to the matching typed column.",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Updated tag together with the device RPC result.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"tag": _tag_object_schema, "rpc": openapi.Schema(type=openapi.TYPE_OBJECT)},
                ),
            ),
            400: openapi.Response(description="Invalid request body."),
            401: _auth_error_response,
            404: openapi.Response(description="Tag not found for the current tenant."),
        },
        tags=["Services, Tags"],
    )


def tags_by_room_get_swagger(**kwargs):
    return swagger_auto_schema(
        operation_summary="List Room Tags",
        operation_description=(
            "Retrieve the room together with its CLIENT_SCOPE attributes and latest telemetry "
            "(SHARED_SCOPE and SERVER_SCOPE attributes are not exposed)."
        ),
        responses={
            200: _tags_list_response,
            401: _auth_error_response,
            404: openapi.Response(description="Room not found for the current tenant."),
        },
        tags=["Services, Tags"],
    )


def tags_by_room_post_swagger(**kwargs):
    return swagger_auto_schema(
        operation_summary="Change Room Tags",
        operation_description=(
            "Apply attribute/telemetry changes to all devices in the room. "
            "SERVER_SCOPE and SHARED_SCOPE attributes are persisted to the database "
            "(SHARED_SCOPE is additionally pushed to devices via RabbitMQ); "
            "CLIENT_SCOPE attributes and telemetry are sent to devices via MQTT RPC."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                required=["type", "items"],
                properties={
                    "type": openapi.Schema(type=openapi.TYPE_STRING, enum=["ATTRIBUTES", "TELEMETRY"]),
                    "scope": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        enum=["CLIENT_SCOPE", "SERVER_SCOPE", "SHARED_SCOPE"],
                    ),
                    "items": openapi.Schema(type=openapi.TYPE_OBJECT, description="Key/value pairs to apply."),
                },
            ),
        ),
        responses={
            200: openapi.Response(
                description="Result of applied changes, grouped by attributes (DB) and telemetry (RPC).",
                examples={"application/json": {"attributes": {}, "telemetry": {}}},
            ),
            400: openapi.Response(description="Invalid request body."),
            401: _auth_error_response,
            404: openapi.Response(description="Room not found for the current tenant."),
        },
        tags=["Services, Tags"],
    )

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

_TAGS = ["Services, Tag Types"]

_not_found_response = openapi.Response(description="Device not found or belongs to another tenant.")

_item_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["tag_section", "tag_sub_section", "tag_name", "tag_type", "tag_ranges"],
    properties={
        "tag_section": openapi.Schema(type=openapi.TYPE_STRING, enum=["ATTRIBUTE", "TELEMETRY"]),
        "tag_sub_section": openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=["SERVER_SCOPE", "CLIENT_SCOPE", "SHARED_SCOPE"],
            x_nullable=True,
            description="Attribute scope; required for ATTRIBUTE, ignored and stored as null for TELEMETRY.",
        ),
        "tag_name": openapi.Schema(type=openapi.TYPE_STRING),
        "tag_type": openapi.Schema(type=openapi.TYPE_STRING, description="Name of the tenant's tag type."),
        # Swagger 2 has no "any type" items, so the item type is described in text.
        "tag_ranges": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            description="Range values of the tag type; each item is any JSON value. Duplicates are collapsed.",
            items=openapi.Schema(type=openapi.TYPE_STRING),
            example=["15-25", True, None],
        ),
    },
)
_list_schema = openapi.Schema(type=openapi.TYPE_ARRAY, items=_item_schema)


def device_tag_types_swagger_retrieve(**kwargs):
    return swagger_auto_schema(
        operation_summary="Retrieve Device Tag Types",
        operation_description="The device's `TAG_TYPES` SERVER_SCOPE attribute; an empty list if it is not set.",
        responses={200: openapi.Response("Tag types.", _list_schema), 404: _not_found_response},
        tags=_TAGS,
    )


def device_tag_types_swagger_update(**kwargs):
    return swagger_auto_schema(
        operation_summary="Set Device Tag Types",
        operation_description=(
            "Replace the device's `TAG_TYPES` SERVER_SCOPE attribute with the given list. "
            "Every `tag_ranges` value must be one of the ranges of the entry's `tag_type`, or lie within "
            'one of its numeric ranges (`"10-50"` or `30` within `"0-100"`). POST and PUT behave the same.'
        ),
        request_body=_list_schema,
        responses={
            200: openapi.Response("Saved tag types.", _list_schema),
            400: openapi.Response(description="Invalid request body."),
            404: _not_found_response,
        },
        tags=_TAGS,
    )

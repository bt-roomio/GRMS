from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from services.serializers.tag_type import TagTypeFilterSerializer, TagTypeSerializer

_TAGS = ["Services, Tag Types"]

_not_found_response = openapi.Response(description="Tag type not found or belongs to another tenant.")
_bad_request_response = openapi.Response(description="Invalid request body.")
_update_responses = {200: TagTypeSerializer(), 400: _bad_request_response, 404: _not_found_response}

# Swagger 2 has no "any type" items, so the item type is described in text.
_tag_ranges_schema = openapi.Schema(
    type=openapi.TYPE_ARRAY,
    description=(
        "Non-empty list of range values; each item is any JSON value (string, number, boolean, null, ...). "
        "Replaces the type's current ranges: unchanged values are kept, new ones are created, "
        "missing ones are removed. Duplicates are collapsed."
    ),
    items=openapi.Schema(type=openapi.TYPE_STRING),
    example=["15-25", "30", True, False, None, "asdf"],
)
_write_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["name", "group", "tag_ranges"],
    properties={
        "name": openapi.Schema(type=openapi.TYPE_STRING),
        "group": openapi.Schema(
            type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID, description="Id of the tenant's tag type group."
        ),
        "tag_ranges": _tag_ranges_schema,
    },
)


def tag_type_swagger_list(**kwargs):
    return swagger_auto_schema(
        operation_summary="List Tag Types",
        operation_description=(
            "Retrieve a paginated list of the tenant's own tag types. "
            "Supports pagination via `page`/`size`, search by name via `search` and ordering via `sort_by`."
        ),
        query_serializer=TagTypeFilterSerializer,
        responses={200: TagTypeSerializer(many=True)},
        tags=_TAGS,
    )


def tag_type_swagger_create(**kwargs):
    return swagger_auto_schema(
        operation_summary="Create Tag Type",
        operation_description="Create a tag type for the current tenant with the given range values.",
        request_body=_write_body,
        responses={201: TagTypeSerializer(), 400: _bad_request_response},
        tags=_TAGS,
    )


def tag_type_swagger_retrieve(**kwargs):
    return swagger_auto_schema(
        operation_summary="Retrieve Tag Type",
        operation_description="Retrieve one of the tenant's own tag types.",
        responses={200: TagTypeSerializer(), 404: _not_found_response},
        tags=_TAGS,
    )


def tag_type_swagger_update(**kwargs):
    return swagger_auto_schema(
        operation_summary="Update Tag Type",
        operation_description="Replace the tag type's name and tag ranges.",
        request_body=_write_body,
        responses=_update_responses,
        tags=_TAGS,
    )


def tag_type_swagger_delete(**kwargs):
    return swagger_auto_schema(
        operation_summary="Delete Tag Type",
        operation_description="Delete the tag type.",
        responses={204: openapi.Response(description="Deleted."), 404: _not_found_response},
        tags=_TAGS,
    )

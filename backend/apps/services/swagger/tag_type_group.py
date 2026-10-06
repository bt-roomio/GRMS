from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from services.serializers.tag_type_group import (
    TagTypeGroupFilterSerializer,
    TagTypeGroupSerializer,
    TagTypeGroupWriteSerializer,
)

_TAGS = ["Services, Tag Type Groups"]

_not_found_response = openapi.Response(description="Tag type group not found or belongs to another tenant.")
_bad_request_response = openapi.Response(description="Invalid request body.")


def tag_type_group_swagger_list(**kwargs):
    return swagger_auto_schema(
        operation_summary="List Tag Type Groups",
        operation_description=(
            "Retrieve a paginated list of the tenant's own tag type groups. "
            "Supports pagination via `page`/`size`, search by name via `search` and ordering via `sort_by`."
        ),
        query_serializer=TagTypeGroupFilterSerializer,
        responses={200: TagTypeGroupSerializer(many=True)},
        tags=_TAGS,
    )


def tag_type_group_swagger_create(**kwargs):
    return swagger_auto_schema(
        operation_summary="Create Tag Type Group",
        operation_description="Create a tag type group for the current tenant.",
        request_body=TagTypeGroupWriteSerializer,
        responses={201: TagTypeGroupSerializer(), 400: _bad_request_response},
        tags=_TAGS,
    )


def tag_type_group_swagger_retrieve(**kwargs):
    return swagger_auto_schema(
        operation_summary="Retrieve Tag Type Group",
        operation_description="Retrieve one of the tenant's own tag type groups.",
        responses={200: TagTypeGroupSerializer(), 404: _not_found_response},
        tags=_TAGS,
    )


def tag_type_group_swagger_update(**kwargs):
    return swagger_auto_schema(
        operation_summary="Update Tag Type Group",
        operation_description="Replace the tag type group's name.",
        request_body=TagTypeGroupWriteSerializer,
        responses={200: TagTypeGroupSerializer(), 400: _bad_request_response, 404: _not_found_response},
        tags=_TAGS,
    )


def tag_type_group_swagger_delete(**kwargs):
    return swagger_auto_schema(
        operation_summary="Delete Tag Type Group",
        operation_description="Delete the tag type group. A group that still has tag types cannot be deleted.",
        responses={
            204: openapi.Response(description="Deleted."),
            404: _not_found_response,
            409: openapi.Response(description="The group still has tag types."),
        },
        tags=_TAGS,
    )

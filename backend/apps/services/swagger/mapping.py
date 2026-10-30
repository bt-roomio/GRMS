from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from services.serializers.mapping import (
    MappingProfileFilterSerializer,
    MappingProfileSerializer,
    MappingProfileWriteSerializer,
)

_PROFILE_TAGS = ["Services, Mapping Profiles"]

_bad_request_response = openapi.Response(description="Invalid request body.")
_profile_not_found_response = openapi.Response(description="Mapping profile not found or belongs to another tenant.")

_RULES_DESCRIPTION = (
    "One rule per tag name: `tag_name` is the attribute or telemetry key of the tags it converts, "
    "`external.value_type` is integer, number, string or boolean, `transform.type` is enum, range, linear "
    "or passthrough, `on_invalid` is reject, skip, clamp or const (writes `on_invalid_value` instead). Rules "
    "replace all rules of the profile. `scope` is tenant (default), room_type or device: a room_type or device "
    "profile names its `room_type` or `device` and applies to the integration of its integrator; a tag takes "
    "its rule from the device profile, then the room type profile, then the integration's profile."
)


def mapping_profile_swagger_list(**kwargs):
    return swagger_auto_schema(
        operation_summary="List Mapping Profiles",
        operation_description="Retrieve a paginated list of the tenant's mapping profiles with their rules.",
        query_serializer=MappingProfileFilterSerializer,
        responses={200: MappingProfileSerializer(many=True)},
        tags=_PROFILE_TAGS,
    )


def mapping_profile_swagger_create(**kwargs):
    return swagger_auto_schema(
        operation_summary="Create Mapping Profile",
        operation_description=f"Create a mapping profile for the current tenant. {_RULES_DESCRIPTION}",
        request_body=MappingProfileWriteSerializer,
        responses={201: MappingProfileSerializer(), 400: _bad_request_response},
        tags=_PROFILE_TAGS,
    )


def mapping_profile_swagger_retrieve(**kwargs):
    return swagger_auto_schema(
        operation_summary="Retrieve Mapping Profile",
        operation_description="Retrieve one of the tenant's mapping profiles with its rules.",
        responses={200: MappingProfileSerializer(), 404: _profile_not_found_response},
        tags=_PROFILE_TAGS,
    )


def mapping_profile_swagger_update(**kwargs):
    return swagger_auto_schema(
        operation_summary="Update Mapping Profile",
        operation_description=(f"Replace the profile and its rules. {_RULES_DESCRIPTION}"),
        request_body=MappingProfileWriteSerializer,
        responses={200: MappingProfileSerializer(), 400: _bad_request_response, 404: _profile_not_found_response},
        tags=_PROFILE_TAGS,
    )


def mapping_profile_swagger_delete(**kwargs):
    return swagger_auto_schema(
        operation_summary="Delete Mapping Profile",
        operation_description="Delete the profile; integrations using it exchange GRMS values as they are.",
        responses={204: openapi.Response(description="Deleted."), 404: _profile_not_found_response},
        tags=_PROFILE_TAGS,
    )

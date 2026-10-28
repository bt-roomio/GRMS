from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from services.serializers.mapping import (
    MappingOverrideFilterSerializer,
    MappingOverrideSerializer,
    MappingProfileFilterSerializer,
    MappingProfileSerializer,
    MappingProfileWriteSerializer,
    MappingTestSerializer,
)

_PROFILE_TAGS = ["Services, Mapping Profiles"]
_OVERRIDE_TAGS = ["Services, Mapping Overrides"]

_bad_request_response = openapi.Response(description="Invalid request body.")
_profile_not_found_response = openapi.Response(description="Mapping profile not found or belongs to another tenant.")
_override_not_found_response = openapi.Response(description="Override not found or belongs to another tenant.")

_RULES_DESCRIPTION = (
    "One rule per tag type. `id` is the rule id, `tag_type` the name of one of the tenant's tag types, "
    "`external.value_type` is integer, number, string or boolean, `transform.type` is enum, range, linear "
    "or passthrough, `validate` holds optional min/max/step/allowed of the external value, `on_invalid` is "
    "reject, skip or clamp. Rules replace all rules of the profile."
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
        operation_description=(
            f"Replace the profile and its rules. {_RULES_DESCRIPTION} Refused when an override of an "
            "integration using the profile no longer fits the new rules."
        ),
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


def mapping_profile_swagger_test(**kwargs):
    return swagger_auto_schema(
        operation_summary="Test Mapping Rule",
        operation_description=(
            "Run one rule of the profile on a value without touching any tag. `to_external` converts a GRMS "
            "value (and `tag_ranges`, if given) to the integrator's form, `to_grms` converts an integrator value "
            "and checks it against `tag_ranges`."
        ),
        request_body=MappingTestSerializer,
        responses={
            200: openapi.Response(
                description="Converted value.",
                examples={"application/json": {"output": 2, "tag_ranges": [1, 2, 3]}},
            ),
            400: openapi.Response(
                description="Invalid body, unknown rule or a value the rule cannot convert.",
                examples={"application/json": {"detail": "No enum pair for the value.", "code": "unmapped"}},
            ),
            404: _profile_not_found_response,
        },
        tags=_PROFILE_TAGS,
    )


def mapping_override_swagger_list(**kwargs):
    return swagger_auto_schema(
        operation_summary="List Mapping Overrides",
        operation_description="Retrieve a paginated list of the overrides of the tenant's integrations.",
        query_serializer=MappingOverrideFilterSerializer,
        responses={200: MappingOverrideSerializer(many=True)},
        tags=_OVERRIDE_TAGS,
    )


def mapping_override_swagger_create(**kwargs):
    return swagger_auto_schema(
        operation_summary="Create Mapping Override",
        operation_description=(
            "Override rules of the integration's mapping profile for a level: tenant (no target), room_type, "
            "room or device (the target id is required). `rule_overrides` maps a rule id to the rule fields it "
            "replaces; the most specific level wins."
        ),
        request_body=MappingOverrideSerializer,
        responses={201: MappingOverrideSerializer(), 400: _bad_request_response},
        tags=_OVERRIDE_TAGS,
    )


def mapping_override_swagger_retrieve(**kwargs):
    return swagger_auto_schema(
        operation_summary="Retrieve Mapping Override",
        responses={200: MappingOverrideSerializer(), 404: _override_not_found_response},
        tags=_OVERRIDE_TAGS,
    )


def mapping_override_swagger_update(**kwargs):
    return swagger_auto_schema(
        operation_summary="Update Mapping Override",
        request_body=MappingOverrideSerializer,
        responses={200: MappingOverrideSerializer(), 400: _bad_request_response, 404: _override_not_found_response},
        tags=_OVERRIDE_TAGS,
    )


def mapping_override_swagger_delete(**kwargs):
    return swagger_auto_schema(
        operation_summary="Delete Mapping Override",
        responses={204: openapi.Response(description="Deleted."), 404: _override_not_found_response},
        tags=_OVERRIDE_TAGS,
    )

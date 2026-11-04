from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from services.serializers.mapping_test import MappingTestSerializer

_issue_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "field": openapi.Schema(
            type=openapi.TYPE_STRING,
            description="Request path of the field: value, inputs.mode, rule.transform.map, "
            "composite_rule.conditions[1].when.mode, ...",
        ),
        "code": openapi.Schema(
            type=openapi.TYPE_STRING,
            description="config, conflict, type, direction, unmapped, invalid (out of range), missing_input, "
            "ambiguous_source; warnings: round_trip, unknown_alias, const.",
        ),
        "message": openapi.Schema(type=openapi.TYPE_STRING),
    },
)

_report_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Whether the value converted."),
        "direction": openapi.Schema(type=openapi.TYPE_STRING),
        "input": openapi.Schema(type=openapi.TYPE_OBJECT, description="The value or the inputs converted (any JSON)."),
        "result": openapi.Schema(
            type=openapi.TYPE_OBJECT, x_nullable=True, description="The converted value (any JSON)."
        ),
        "actions": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            x_nullable=True,
            description="Composite to_grms: the writes that would run, in order "
            "({alias, tag_name, source, value, required}, with tag_id and device given a room).",
            items=openapi.Schema(type=openapi.TYPE_OBJECT),
        ),
        "skipped": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="The rule drops the value (skip)."),
        "errors": openapi.Schema(type=openapi.TYPE_ARRAY, items=_issue_schema),
        "warnings": openapi.Schema(type=openapi.TYPE_ARRAY, items=_issue_schema),
        "unavailable": openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description="Composite to_external with live inputs: alias -> missing_input or ambiguous_source.",
        ),
        "tag_ranges": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_STRING),
            description="Plain to_external with tag_ranges: the ranges in the integrator's form.",
        ),
        "rule": openapi.Schema(
            type=openapi.TYPE_OBJECT, description="Where the rule came from: {source, profile?, integration?, scope?}."
        ),
    },
)


def mapping_test_swagger(**kwargs):
    return swagger_auto_schema(
        operation_summary="Test Mapping Rule",
        operation_description=(
            "Convert one value with a mapping rule without saving anything or sending any RPC. The rule is "
            "inline (rule, composite_rule) or saved (profile or integration with tag_name or composite_id; "
            "room or device pick the effective rule of the device -> room_type -> tenant chain). A conversion "
            "that fails answers 200 with success: false and structured errors; a malformed request answers 400."
        ),
        request_body=MappingTestSerializer,
        responses={
            200: openapi.Response(
                description="The dry run.",
                schema=_report_schema,
                examples={
                    "application/json": {
                        "success": True,
                        "direction": "to_grms",
                        "input": 2,
                        "result": None,
                        "actions": [
                            {
                                "alias": "mode",
                                "tag_name": "AC Mode",
                                "source": "telemetry",
                                "value": "Cool",
                                "required": True,
                            },
                            {
                                "alias": "power",
                                "tag_name": "AC ON OFF",
                                "source": "telemetry",
                                "value": 1,
                                "required": True,
                            },
                        ],
                        "skipped": False,
                        "errors": [],
                        "warnings": [],
                        "rule": {"source": "inline"},
                    }
                },
            ),
            400: openapi.Response(description="Malformed request, or the saved rule is not found."),
            403: openapi.Response(description="No services.view_mappingprofile permission."),
            404: openapi.Response(description="Profile, integration, room or device of another tenant."),
        },
        tags=["Services, Mapping Profiles"],
    )

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from alarms.serializers.rule import (
    AlarmRuleBulkSerializer,
    AlarmRuleFilterParams,
    AlarmRulePreviewSerializer,
    AlarmRuleSerializer,
    AlarmRuleTemplateSerializer,
)

TAG = "Alarm Rules"

NOT_FOUND = openapi.Response(
    description="Not found",
    examples={"application/json": {"detail": "Not found."}},
)

PREVIEW_RESULT = openapi.Response(
    description="How many devices the rules would match right now",
    examples={
        "application/json": {
            "device_count": 42,
            "alarms": [
                {
                    "alarmType": "High Temperature",
                    "create_rules": [{"severity": "MINOR", "spec": "DURATION", "matched_count": 2, "sample": []}],
                    "clear_rule": None,
                }
            ],
        }
    },
)


def list_swagger():
    return swagger_auto_schema(
        tags=[TAG],
        query_serializer=AlarmRuleFilterParams(),
        responses={200: AlarmRuleSerializer(many=True)},
    )


def create_swagger():
    return swagger_auto_schema(
        tags=[TAG],
        request_body=AlarmRuleSerializer,
        operation_description=(
            "The rule body is ThingsBoard's DeviceProfileAlarm (camelCase) plus device_profile and enabled."
        ),
        responses={201: AlarmRuleSerializer()},
    )


def retrieve_swagger():
    return swagger_auto_schema(tags=[TAG], responses={200: AlarmRuleSerializer(), 404: NOT_FOUND})


def update_swagger():
    return swagger_auto_schema(
        tags=[TAG],
        request_body=AlarmRuleSerializer,
        operation_description='Partial: send only what changes, for example {"enabled": false}.',
        responses={200: AlarmRuleSerializer(), 404: NOT_FOUND},
    )


def delete_swagger():
    return swagger_auto_schema(
        tags=[TAG],
        operation_description="Remove the rule. Alarms it already raised stay in the journal.",
        responses={204: openapi.Response(description="Deleted"), 404: NOT_FOUND},
    )


def bulk_swagger():
    return swagger_auto_schema(
        tags=[TAG],
        request_body=AlarmRuleBulkSerializer,
        operation_description=(
            "Replace every rule of one profile. Rules are matched by alarmType: existing ones are updated, "
            "missing ones deleted. This is the import path for a ThingsBoard profile export."
        ),
        responses={200: AlarmRuleSerializer(many=True)},
    )


def preview_swagger():
    return swagger_auto_schema(
        tags=[TAG],
        request_body=AlarmRulePreviewSerializer,
        operation_description=(
            "Dry run against the profile's devices. Omit 'alarms' to run the rules already stored. "
            "spec and schedule are ignored: the answer is 'does the condition hold now'."
        ),
        responses={200: PREVIEW_RESULT},
    )


def templates_swagger():
    return swagger_auto_schema(
        tags=[TAG],
        operation_description=(
            "Ready-made rules for the builder. Each 'rule' is a DeviceProfileAlarm that can be posted "
            "to /alarms/rules/ as is; 'requires' lists the keys it needs, to be checked against available-keys."
        ),
        responses={200: AlarmRuleTemplateSerializer(many=True)},
    )

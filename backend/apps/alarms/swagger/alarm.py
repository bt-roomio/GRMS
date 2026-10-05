from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from alarms.serializers.alarm import (
    AlarmAssignSerializer,
    AlarmBulkSerializer,
    AlarmCommentCreateSerializer,
    AlarmCommentSerializer,
    AlarmFilterParams,
    AlarmSerializer,
    AlarmSummaryParams,
    AvailableKeysParams,
)

TAG = "Alarms"

NOT_FOUND = openapi.Response(
    description="Not found",
    examples={"application/json": {"detail": "Not found."}},
)

FORBIDDEN = openapi.Response(
    description="Not the author, or a system comment",
    examples={"application/json": {"detail": "You can only edit your own comments."}},
)

BULK_RESULT = openapi.Response(
    description="How many rows the call actually changed",
    examples={"application/json": {"updated": 12, "requested": 15}},
)


def list_swagger():
    return swagger_auto_schema(tags=[TAG], query_serializer=AlarmFilterParams(), responses={200: AlarmSerializer()})


def retrieve_swagger():
    return swagger_auto_schema(tags=[TAG], responses={200: AlarmSerializer(), 404: NOT_FOUND})


def ack_swagger():
    return swagger_auto_schema(tags=[TAG], request_body=None, responses={200: AlarmSerializer(), 404: NOT_FOUND})


def clear_swagger():
    return swagger_auto_schema(tags=[TAG], request_body=None, responses={200: AlarmSerializer(), 404: NOT_FOUND})


def assign_swagger():
    return swagger_auto_schema(
        tags=[TAG],
        request_body=AlarmAssignSerializer,
        responses={200: AlarmSerializer(), 404: NOT_FOUND},
    )


def comments_list_swagger():
    return swagger_auto_schema(tags=[TAG], responses={200: AlarmCommentSerializer(many=True)})


def comment_create_swagger():
    return swagger_auto_schema(
        tags=[TAG],
        request_body=AlarmCommentCreateSerializer,
        responses={201: AlarmCommentSerializer()},
    )


def delete_swagger():
    return swagger_auto_schema(
        tags=[TAG],
        operation_description="Remove an alarm and its comments for good. The journal loses the incident.",
        responses={204: openapi.Response(description="Deleted"), 404: NOT_FOUND},
    )


def comment_update_swagger():
    return swagger_auto_schema(
        tags=[TAG],
        request_body=AlarmCommentCreateSerializer,
        operation_description="Edit your own comment. System comments are read-only.",
        responses={200: AlarmCommentSerializer(), 403: FORBIDDEN, 404: NOT_FOUND},
    )


def comment_delete_swagger():
    return swagger_auto_schema(
        tags=[TAG],
        operation_description="Delete your own comment. System comments are read-only.",
        responses={204: openapi.Response(description="Deleted"), 403: FORBIDDEN, 404: NOT_FOUND},
    )


def bulk_ack_swagger():
    return swagger_auto_schema(
        tags=[TAG],
        request_body=AlarmBulkSerializer,
        operation_description="Acknowledge every listed alarm. Already acknowledged ones are skipped.",
        responses={200: BULK_RESULT},
    )


def bulk_clear_swagger():
    return swagger_auto_schema(
        tags=[TAG],
        request_body=AlarmBulkSerializer,
        operation_description="Clear every listed alarm. Already cleared ones are skipped.",
        responses={200: BULK_RESULT},
    )


def summary_swagger():
    return swagger_auto_schema(
        tags=[TAG],
        query_serializer=AlarmSummaryParams(),
        responses={
            200: openapi.Response(
                description="Counters by type and severity",
                examples={
                    "application/json": {
                        "total": 12,
                        "active": 5,
                        "unacknowledged": 3,
                        "by_severity": {"CRITICAL": 1, "MAJOR": 4},
                        "by_type": {"Device Offline": 4, "High Temperature": 1},
                    }
                },
            )
        },
    )


def types_swagger():
    return swagger_auto_schema(
        tags=[TAG],
        responses={200: openapi.Response(description="Alarm types seen for this tenant")},
    )


def available_keys_swagger():
    return swagger_auto_schema(
        tags=[TAG],
        query_serializer=AvailableKeysParams(),
        responses={
            200: openapi.Response(
                description="Keys the rule builder can offer",
                examples={
                    "application/json": {
                        "timeseries": ["Room Temperature", "Occupancy State"],
                        "attributes": ["active", "notifyOnOffline"],
                        "entity_fields": ["name", "is_gateway"],
                    }
                },
            )
        },
    )


def preview_swagger():
    return swagger_auto_schema(
        tags=["Main, Device Profile"],
        responses={
            200: openapi.Response(
                description="How many devices the rules would match right now",
                examples={
                    "application/json": {
                        "device_count": 120,
                        "alarms": [
                            {
                                "alarmType": "High Temperature",
                                "create_rules": [{"severity": "MINOR", "matched_count": 2, "sample": []}],
                            }
                        ],
                    }
                },
            )
        },
    )

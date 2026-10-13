from rest_framework import serializers

from alarms.constants import AlarmSeverity, AlarmStatus
from alarms.models import Alarm, AlarmComment
from core.utils.serializers import ValidatorSerializer
from users.serializers.user import SimpleUserSerializer

STATUS_CHOICES = ("ACTIVE", "CLEARED", "UNACK", "ACK", *AlarmStatus.values)


class AlarmSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    duration_ms = serializers.IntegerField(read_only=True)
    originator_name = serializers.CharField(source="originator.name", read_only=True)
    room_number = serializers.CharField(source="room.number", read_only=True, allow_null=True)
    assignee = SimpleUserSerializer(read_only=True)

    class Meta:
        model = Alarm
        fields = (
            "id",
            "alarm_type",
            "severity",
            "status",
            "acknowledged",
            "cleared",
            "start_ts",
            "end_ts",
            "ack_ts",
            "clear_ts",
            "duration_ms",
            "details",
            "tenant",
            "originator",
            "originator_name",
            "room",
            "room_number",
            "assignee",
            "assign_ts",
            "propagate_entity_ids",
            "notified_at",
            "created_at",
        )
        read_only_fields = fields


class SimpleAlarmSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    originator_name = serializers.CharField(source="originator.name", read_only=True)

    class Meta:
        model = Alarm
        fields = ("id", "alarm_type", "severity", "status", "start_ts", "originator", "originator_name", "details")


class AlarmCommentSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)

    class Meta:
        model = AlarmComment
        fields = ("id", "alarm_comment_type", "comment", "user", "created_at")
        read_only_fields = fields


class AlarmCommentCreateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=4000)

    class Meta:
        ref_name = "AlarmCommentCreate"


class AlarmAssignSerializer(ValidatorSerializer):
    # null unassigns — the same endpoint both ways, as in TB.
    assignee = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        ref_name = "AlarmAssign"


class AlarmBulkSerializer(ValidatorSerializer):
    """
    Acknowledging a gateway outage one row at a time is not an operation anyone
    performs twice; TB offers the same thing from the table's multi-select.
    """

    ids = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=500)

    class Meta:
        ref_name = "AlarmBulk"


class AlarmFilterParams(ValidatorSerializer):
    SORT_FIELDS = (
        "start_ts",
        "-start_ts",
        "end_ts",
        "-end_ts",
        "severity",
        "-severity",
        "alarm_type",
        "-alarm_type",
    )

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=15)
    alarm_type = serializers.ListField(child=serializers.CharField(max_length=255), required=False)
    severity = serializers.ListField(child=serializers.ChoiceField(choices=AlarmSeverity.choices), required=False)
    status = serializers.ChoiceField(choices=STATUS_CHOICES, required=False)
    device = serializers.UUIDField(required=False)
    room = serializers.UUIDField(required=False)
    # A user id, or "none" for the unassigned ones.
    assignee = serializers.CharField(required=False)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)


class AlarmSummaryParams(ValidatorSerializer):
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
    status = serializers.ChoiceField(choices=STATUS_CHOICES, required=False)


class AvailableKeysParams(ValidatorSerializer):
    search_value = serializers.CharField(required=False)

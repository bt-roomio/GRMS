from rest_framework import serializers

from alarms.serializers.rules.alarm_condition import AlarmConditionSerializer
from alarms.serializers.rules.schedule import AlarmScheduleSerializer


class AlarmRuleSerializer(serializers.Serializer):
    """``AlarmRule`` — one severity's condition, when it applies and what it says."""

    condition = AlarmConditionSerializer()
    schedule = AlarmScheduleSerializer(required=False, allow_null=True)
    # Template with ${key} placeholders, rendered into Alarm.details["message"].
    alarmDetails = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    dashboardId = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        ref_name = "AlarmRule"

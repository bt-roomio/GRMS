from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers
from rest_framework.settings import api_settings

from alarms.constants import (
    SCHEDULE_ANY_TIME,
    SCHEDULE_CUSTOM,
    SCHEDULE_SPECIFIC_TIME,
    SCHEDULE_TYPES,
)

MS_PER_DAY = 24 * 60 * 60 * 1000


class TimezoneField(serializers.CharField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise serializers.ValidationError(f"Unknown timezone '{value}'.") from exc
        return value


class AnyTimeScheduleSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[SCHEDULE_ANY_TIME])

    class Meta:
        ref_name = "AlarmAnyTimeSchedule"


class SpecificTimeScheduleSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[SCHEDULE_SPECIFIC_TIME])
    timezone = TimezoneField(required=False, default="UTC")
    # ISO weekdays, Monday = 1.
    daysOfWeek = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=7),
        allow_empty=False,
    )
    # Milliseconds from midnight in the schedule's own timezone.
    startsOn = serializers.IntegerField(min_value=0, max_value=MS_PER_DAY)
    endsOn = serializers.IntegerField(min_value=0, max_value=MS_PER_DAY)

    class Meta:
        ref_name = "AlarmSpecificTimeSchedule"


class CustomTimeScheduleItemSerializer(serializers.Serializer):
    enabled = serializers.BooleanField(default=False)
    dayOfWeek = serializers.IntegerField(min_value=1, max_value=7)
    startsOn = serializers.IntegerField(min_value=0, max_value=MS_PER_DAY, default=0)
    endsOn = serializers.IntegerField(min_value=0, max_value=MS_PER_DAY, default=0)

    class Meta:
        ref_name = "AlarmCustomTimeScheduleItem"


class CustomTimeScheduleSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[SCHEDULE_CUSTOM])
    timezone = TimezoneField(required=False, default="UTC")
    items = CustomTimeScheduleItemSerializer(many=True, allow_empty=False)

    class Meta:
        ref_name = "AlarmCustomTimeSchedule"


SCHEDULE_SERIALIZERS = {
    SCHEDULE_ANY_TIME: AnyTimeScheduleSerializer,
    SCHEDULE_SPECIFIC_TIME: SpecificTimeScheduleSerializer,
    SCHEDULE_CUSTOM: CustomTimeScheduleSerializer,
}


class AlarmScheduleSerializer(serializers.Serializer):
    """``AlarmSchedule`` — polymorphic on ``type``."""

    class Meta:
        ref_name = "AlarmSchedule"

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError(
                {api_settings.NON_FIELD_ERRORS_KEY: "Expected an object describing a schedule."}
            )

        schedule_type = data.get("type")
        if schedule_type not in SCHEDULE_TYPES:
            raise serializers.ValidationError({"type": f"Must be one of {list(SCHEDULE_TYPES)}."})

        serializer = SCHEDULE_SERIALIZERS[schedule_type](data=data)
        serializer.is_valid(raise_exception=True)
        return dict(serializer.validated_data)

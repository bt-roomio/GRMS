from rest_framework import serializers

from alarms.constants import AlarmSeverity
from alarms.serializers.rules.alarm_rule import AlarmRuleSerializer


class DeviceProfileAlarmSerializer(serializers.Serializer):
    """
    ``DeviceProfileAlarm`` — one alarm type on a device profile.

    Rules have no table of their own: they live in
    ``DeviceProfile.profile_data["alarms"]``, which is where TB keeps them, and
    apply to every device of the profile. There is no targeting.
    """

    id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    alarmType = serializers.CharField(max_length=255)
    createRules = serializers.DictField(child=AlarmRuleSerializer(), allow_empty=False)
    clearRule = AlarmRuleSerializer(required=False, allow_null=True)

    propagate = serializers.BooleanField(required=False, default=False)
    propagateRelationTypes = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        default=list,
    )
    propagateToOwner = serializers.BooleanField(required=False, default=False)
    propagateToTenant = serializers.BooleanField(required=False, default=False)

    class Meta:
        ref_name = "DeviceProfileAlarm"

    def validate_createRules(self, value):
        unknown = set(value) - set(AlarmSeverity.values)
        if unknown:
            raise serializers.ValidationError(f"Unknown severities: {sorted(unknown)}.")
        return value


def validate_profile_alarms(alarms, raise_exception: bool = True):
    """
    Validate the whole ``profile_data["alarms"]`` list.

    Returns the cleaned list, still camelCase, ready to be written back into
    ``profile_data`` unchanged.
    """
    if alarms in (None, ""):
        return []

    if not isinstance(alarms, list):
        raise serializers.ValidationError({"alarms": "Expected a list of alarm rules."})

    serializer = DeviceProfileAlarmSerializer(data=alarms, many=True)
    if not serializer.is_valid():
        if raise_exception:
            raise serializers.ValidationError({"alarms": serializer.errors})
        return []

    cleaned = [dict(alarm) for alarm in serializer.validated_data]

    seen, duplicates = set(), set()
    for alarm in cleaned:
        alarm_type = alarm["alarmType"]
        if alarm_type in seen:
            duplicates.add(alarm_type)
        seen.add(alarm_type)

    if duplicates:
        # Two rules of one type on one profile would fight over the same active
        # alarm row, which the partial unique index would then reject at random.
        raise serializers.ValidationError({"alarms": f"Duplicate alarmType: {sorted(duplicates)}."})

    return cleaned

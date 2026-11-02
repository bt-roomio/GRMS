from rest_framework import serializers
from rest_framework.settings import api_settings

from alarms.constants import (
    SPEC_DURATION,
    SPEC_REPEATING,
    SPEC_SIMPLE,
    SPEC_TYPES,
    TIME_UNITS,
)
from alarms.serializers.rules.predicate_value import FilterPredicateValueSerializer


class DurationSpecSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[SPEC_DURATION])
    unit = serializers.ChoiceField(choices=TIME_UNITS)
    # A FilterPredicateValue, so the duration itself can come from an attribute.
    predicate = FilterPredicateValueSerializer()

    class Meta:
        ref_name = "AlarmDurationSpec"

    def validate_predicate(self, value):
        default = value.get("defaultValue")
        if default is not None and (not isinstance(default, (int, float)) or default <= 0):
            raise serializers.ValidationError("A DURATION needs a positive 'defaultValue'.")
        return value


class RepeatingSpecSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[SPEC_REPEATING])
    predicate = FilterPredicateValueSerializer()

    class Meta:
        ref_name = "AlarmRepeatingSpec"

    def validate_predicate(self, value):
        default = value.get("defaultValue")
        if default is not None and (not isinstance(default, int) or isinstance(default, bool) or default < 1):
            raise serializers.ValidationError("A REPEATING count must be an integer of at least 1.")
        return value


class SimpleSpecSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[SPEC_SIMPLE])

    class Meta:
        ref_name = "AlarmSimpleSpec"


SPEC_SERIALIZERS = {
    SPEC_SIMPLE: SimpleSpecSerializer,
    SPEC_DURATION: DurationSpecSerializer,
    SPEC_REPEATING: RepeatingSpecSerializer,
}


class AlarmConditionSpecSerializer(serializers.Serializer):
    """``AlarmConditionSpec`` — polymorphic on ``type``, SIMPLE when omitted."""

    class Meta:
        ref_name = "AlarmConditionSpec"

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError(
                {api_settings.NON_FIELD_ERRORS_KEY: "Expected an object describing a condition spec."}
            )

        spec_type = data.get("type", SPEC_SIMPLE)
        if spec_type not in SPEC_TYPES:
            raise serializers.ValidationError({"type": f"Must be one of {list(SPEC_TYPES)}."})

        serializer = SPEC_SERIALIZERS[spec_type](data={**data, "type": spec_type})
        serializer.is_valid(raise_exception=True)
        return dict(serializer.validated_data)

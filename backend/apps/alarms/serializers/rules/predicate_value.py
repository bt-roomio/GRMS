from rest_framework import serializers

from alarms.serializers.rules.dynamic_value import DynamicValueSerializer


class FilterPredicateValueSerializer(serializers.Serializer):
    """``FilterPredicateValue<T>`` — a constant, an attribute reference, or both."""

    defaultValue = serializers.JSONField(required=False, allow_null=True)
    # Kept only so a rule copied out of TB survives the round trip untouched.
    userValue = serializers.JSONField(required=False, allow_null=True)
    dynamicValue = DynamicValueSerializer(required=False, allow_null=True)

    class Meta:
        ref_name = "AlarmFilterPredicateValue"

    def validate(self, attrs):
        if attrs.get("defaultValue") is None and not attrs.get("dynamicValue"):
            raise serializers.ValidationError("Either 'defaultValue' or 'dynamicValue' is required.")
        return attrs

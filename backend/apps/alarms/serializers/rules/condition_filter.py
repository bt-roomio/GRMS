from rest_framework import serializers

from alarms.constants import (
    ENTITY_FIELD_WHITELIST,
    KEY_CONSTANT,
    KEY_ENTITY_FIELD,
    KEY_TYPES,
    VALUE_TYPE_TO_PREDICATE,
    VALUE_TYPES,
)
from alarms.serializers.rules.predicate import KeyFilterPredicateSerializer, leaf_predicate_types


class AlarmConditionFilterKeySerializer(serializers.Serializer):
    """``AlarmConditionFilterKey`` — where the compared value comes from."""

    type = serializers.ChoiceField(choices=KEY_TYPES)
    key = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)

    class Meta:
        ref_name = "AlarmConditionFilterKey"


class AlarmConditionFilterSerializer(serializers.Serializer):
    key = AlarmConditionFilterKeySerializer()
    valueType = serializers.ChoiceField(choices=VALUE_TYPES)
    # Only meaningful for a CONSTANT key: the literal the predicate compares.
    value = serializers.JSONField(required=False, allow_null=True)
    predicate = KeyFilterPredicateSerializer()

    class Meta:
        ref_name = "AlarmConditionFilter"

    def validate(self, attrs):
        key = attrs["key"]

        if key["type"] == KEY_CONSTANT:
            if attrs.get("value") is None:
                raise serializers.ValidationError({"value": "A CONSTANT key needs a 'value'."})
        elif not (key.get("key") or "").strip():
            raise serializers.ValidationError({"key": {"key": "This field may not be blank."}})

        if key["type"] == KEY_ENTITY_FIELD and key.get("key") not in ENTITY_FIELD_WHITELIST:
            # GRMS deviation: TB resolves arbitrary entity fields; here the set
            # a rule may reach is fixed.
            raise serializers.ValidationError(
                {"key": {"key": f"ENTITY_FIELD must be one of {list(ENTITY_FIELD_WHITELIST)}."}}
            )

        expected = VALUE_TYPE_TO_PREDICATE[attrs["valueType"]]
        mismatched = leaf_predicate_types(attrs["predicate"]) - {expected}
        if mismatched:
            raise serializers.ValidationError(
                {"predicate": f"valueType {attrs['valueType']} needs {expected} predicates, got {sorted(mismatched)}."}
            )

        return attrs

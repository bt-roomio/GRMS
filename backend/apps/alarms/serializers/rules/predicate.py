from rest_framework import serializers
from rest_framework.settings import api_settings

from alarms.constants import (
    BOOLEAN_OPERATIONS,
    COMPLEX_OPERATIONS,
    MAX_COMPLEX_DEPTH,
    NUMERIC_OPERATIONS,
    PREDICATE_BOOLEAN,
    PREDICATE_COMPLEX,
    PREDICATE_NUMERIC,
    PREDICATE_STRING,
    PREDICATE_TYPES,
    STRING_OPERATIONS,
)
from alarms.serializers.rules.predicate_value import FilterPredicateValueSerializer

# DRF can only wrap dict-shaped errors coming out of to_internal_value.
NON_FIELD = api_settings.NON_FIELD_ERRORS_KEY


class NumericPredicateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[PREDICATE_NUMERIC])
    operation = serializers.ChoiceField(choices=NUMERIC_OPERATIONS)
    value = FilterPredicateValueSerializer()

    class Meta:
        ref_name = "AlarmNumericPredicate"


class BooleanPredicateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[PREDICATE_BOOLEAN])
    operation = serializers.ChoiceField(choices=BOOLEAN_OPERATIONS)
    value = FilterPredicateValueSerializer()

    class Meta:
        ref_name = "AlarmBooleanPredicate"


class StringPredicateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[PREDICATE_STRING])
    operation = serializers.ChoiceField(choices=STRING_OPERATIONS)
    value = FilterPredicateValueSerializer()
    ignoreCase = serializers.BooleanField(required=False, default=False)

    class Meta:
        ref_name = "AlarmStringPredicate"


SIMPLE_PREDICATES = {
    PREDICATE_NUMERIC: NumericPredicateSerializer,
    PREDICATE_BOOLEAN: BooleanPredicateSerializer,
    PREDICATE_STRING: StringPredicateSerializer,
}


class KeyFilterPredicateSerializer(serializers.Serializer):
    """
    Polymorphic on ``type``, recursive through ``COMPLEX``.

    ``COMPLEX`` is what buys nested AND/OR for free; the depth cap is what stops
    a hand-written profile from walking the evaluator into recursion.
    """

    class Meta:
        ref_name = "AlarmKeyFilterPredicate"

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError({NON_FIELD: "Expected an object describing a predicate."})

        predicate_type = data.get("type")
        if predicate_type not in PREDICATE_TYPES:
            raise serializers.ValidationError({"type": f"Must be one of {list(PREDICATE_TYPES)}."})

        if predicate_type != PREDICATE_COMPLEX:
            serializer = SIMPLE_PREDICATES[predicate_type](data=data)
            serializer.is_valid(raise_exception=True)
            return dict(serializer.validated_data)

        return self._complex(data)

    def _complex(self, data):
        depth = self.context.get("predicate_depth", 1)
        if depth > MAX_COMPLEX_DEPTH:
            raise serializers.ValidationError(
                {"predicates": f"Nested COMPLEX predicates may not go deeper than {MAX_COMPLEX_DEPTH}."}
            )

        operation = data.get("operation")
        if operation not in COMPLEX_OPERATIONS:
            raise serializers.ValidationError({"operation": f"Must be one of {list(COMPLEX_OPERATIONS)}."})

        predicates = data.get("predicates")
        if not isinstance(predicates, list) or not predicates:
            raise serializers.ValidationError({"predicates": "A COMPLEX predicate needs at least one child."})

        errors, children = {}, []
        for index, child in enumerate(predicates):
            serializer = KeyFilterPredicateSerializer(
                data=child,
                context={**self.context, "predicate_depth": depth + 1},
            )
            try:
                # `.errors` is not usable here: a child can fail with a
                # non-field list, which DRF's ReturnDict refuses to wrap.
                serializer.is_valid(raise_exception=True)
            except serializers.ValidationError as exc:
                errors[str(index)] = exc.detail
            else:
                children.append(dict(serializer.validated_data))

        if errors:
            raise serializers.ValidationError({"predicates": errors})

        return {"type": PREDICATE_COMPLEX, "operation": operation, "predicates": children}


def leaf_predicate_types(predicate: dict) -> set[str]:
    """Every non-COMPLEX type reachable from this predicate."""
    predicate_type = predicate.get("type")
    if predicate_type != PREDICATE_COMPLEX:
        return {str(predicate_type)}

    found: set[str] = set()
    for child in predicate.get("predicates") or []:
        found |= leaf_predicate_types(child)
    return found

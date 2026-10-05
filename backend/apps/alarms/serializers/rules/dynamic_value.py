from rest_framework import serializers

from alarms.constants import DYNAMIC_SOURCE_TYPES


class DynamicValueSerializer(serializers.Serializer):
    """
    ``org.thingsboard.server.common.data.query.DynamicValue``.

    Points a predicate at an attribute instead of a constant, which is how a
    per-room temperature threshold is expressed without a special case anywhere
    in the evaluator.
    """

    sourceType = serializers.ChoiceField(choices=DYNAMIC_SOURCE_TYPES)
    sourceAttribute = serializers.CharField(max_length=255)
    # When the source entity has no such attribute, walk up device → room →
    # tenant instead of falling back to defaultValue immediately.
    inherit = serializers.BooleanField(required=False, default=False)

    class Meta:
        ref_name = "AlarmDynamicValue"

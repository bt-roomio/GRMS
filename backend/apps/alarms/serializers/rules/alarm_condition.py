from rest_framework import serializers

from alarms.constants import SPEC_SIMPLE
from alarms.serializers.rules.condition_filter import AlarmConditionFilterSerializer
from alarms.serializers.rules.condition_spec import AlarmConditionSpecSerializer


class AlarmConditionSerializer(serializers.Serializer):
    """
    ``AlarmCondition``: a list of filters plus a spec.

    The filters are ANDed — OR lives inside a single filter's COMPLEX predicate,
    exactly as in TB.
    """

    condition = AlarmConditionFilterSerializer(many=True, allow_empty=False)
    spec = AlarmConditionSpecSerializer(required=False, default=lambda: {"type": SPEC_SIMPLE})

    class Meta:
        ref_name = "AlarmCondition"

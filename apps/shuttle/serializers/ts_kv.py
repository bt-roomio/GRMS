from core.utils.aggregation_func import AGGREGATION_FUNCTIONS
from core.utils.serializers import ValidatorSerializer
from core.utils.unix_timestamp import TimestampField
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class TsKvFilterPath(ValidatorSerializer):
    entity_type = serializers.ChoiceField(choices=["DEVICE"])
    entity_id = serializers.UUIDField()


class TsKvFilterParams(ValidatorSerializer):
    AGG = AGGREGATION_FUNCTIONS
    default_error_messages = {
        # TODO: None - should be in list of aggregate functions.
        "invalid_choice": _('"{input}" is not a valid choice. Select from the list [Min, Max, Avg, Sum, Count]')
    }

    keys = serializers.ListField(child=serializers.CharField())
    start_ts = TimestampField()
    end_ts = TimestampField()
    interval = serializers.IntegerField(default=60)  # Default is 60sec
    agg = serializers.ChoiceField(choices=AGG, default=AGG["Min"], error_messages=default_error_messages)
    limit = serializers.IntegerField(default=100)

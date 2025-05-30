from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from core.serializers.dynamic import DynamicField
from core.utils.aggregation_func import AGGREGATION_FUNCTIONS
from core.utils.serializers import ValidatorSerializer
from main.models import Device


class TsKvHistorySerializer(serializers.Serializer):
    ts = serializers.DateTimeField()
    key_name = serializers.CharField()
    value = DynamicField()


class TsKvHistoryFilterParams(ValidatorSerializer):
    AGG = AGGREGATION_FUNCTIONS
    default_error_messages = {
        "invalid_choice": _('"{input}" is not a valid choice. Select from the list [Min, Max, Avg, Sum, Count, None]')
    }

    device = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all(), required=False)
    room = serializers.CharField(required=False)
    keys = serializers.ListField(child=serializers.CharField())
    start_ts = serializers.DateTimeField(allow_null=True, required=False)
    interval = serializers.CharField(allow_null=True, required=False)
    sort_by = serializers.ListField(
        child=serializers.ChoiceField(choices=["-interval_ts", "interval_ts"], default="interval_ts")
    )
    agg = serializers.ChoiceField(choices=AGG, default="Avg")
    limit = serializers.IntegerField(default=100, max_value=1000)
    auto_fill = serializers.BooleanField(default=True)

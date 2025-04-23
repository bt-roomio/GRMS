from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from core.serializers.dynamic import DynamicField
from core.utils.aggregation_func import AGGREGATION_FUNCTIONS
from core.utils.serializers import ValidatorSerializer
from core.utils.unix_timestamp import TimestampField
from main.models import Device, Room, Tenant


class GatewayLogsSerializer(serializers.Serializer):
    ts = serializers.IntegerField()
    key_name = serializers.CharField()
    value = DynamicField()


class GatewayLogsFilterParams(ValidatorSerializer):
    SORT_FIELDS = (
        "ts",
        "-ts",
    )

    device = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all())
    key = serializers.CharField()
    start_ts = serializers.DateTimeField()
    end_ts = serializers.DateTimeField()
    page = serializers.IntegerField(default=1, min_value=1)
    size = serializers.IntegerField(default=15, max_value=500)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)


class TsKvSerializer(serializers.Serializer):
    ts = serializers.IntegerField()
    key_name = serializers.CharField()
    value = DynamicField()


class TsKvFilterPath(ValidatorSerializer):
    entity_type = serializers.ChoiceField(choices=["DEVICE"], required=False)
    entity_id = serializers.UUIDField(required=False)

    tenant_id = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all(), required=False)
    room_id = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all(), required=False)

    def validate(self, data):  # pyright: ignore
        has_entity_id = data.get("entity_id") is not None
        has_tenant = data.get("tenant_id") is not None
        has_room = data.get("room_id") is not None

        # Enforce that only one of the two groups is provided
        if has_entity_id and (has_tenant or has_room):
            raise serializers.ValidationError("Provide either 'entity_id' or 'tenant_id' and 'room_id', not both.")

        # When tenant or room is provided, ensure both are present.
        if has_tenant != has_room:
            raise serializers.ValidationError("Both 'tenant_id' and 'room_id' must be provided together.")

        # At least one valid group must be provided.
        if not (has_entity_id or (has_tenant and has_room)):
            raise serializers.ValidationError("You must provide either 'entity_id' or both 'tenant_id' and 'room_id'.")

        return data


class TagLogsFilterParams(ValidatorSerializer):
    SORT_FIELDS = (
        "ts",
        "-ts",
    )
    device = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all())
    keys = serializers.ListField(child=serializers.CharField())
    start_ts = serializers.DateTimeField()
    page = serializers.IntegerField(default=1, min_value=1)
    size = serializers.IntegerField(default=15, max_value=500)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)


class TsKvFilterParams(ValidatorSerializer):
    AGG = AGGREGATION_FUNCTIONS
    default_error_messages = {
        "invalid_choice": _('"{input}" is not a valid choice. Select from the list [Min, Max, Avg, Sum, Count, None]')
    }

    keys = serializers.ListField(child=serializers.CharField())
    start_ts = TimestampField()
    end_ts = TimestampField()
    interval = serializers.IntegerField(default=60)  # Default is 60sec
    agg = serializers.ChoiceField(choices=AGG, default=AGG["Min"], error_messages=default_error_messages)
    limit = serializers.IntegerField(default=100)

"""
DRF mirrors of the ThingsBoard alarm-rule classes.

Field names stay camelCase on purpose: rules live in
``DeviceProfile.profile_data["alarms"]`` in exactly the shape TB writes them, so
a profile exported from ThingsBoard can be pasted in unchanged and anyone who
read the TB docs already knows the contract. ``validated_data`` therefore comes
back camelCase too and is stored verbatim — no lossy snake_case round trip.
"""

from alarms.serializers.rules.alarm_condition import AlarmConditionSerializer
from alarms.serializers.rules.alarm_rule import AlarmRuleSerializer
from alarms.serializers.rules.condition_filter import (
    AlarmConditionFilterKeySerializer,
    AlarmConditionFilterSerializer,
)
from alarms.serializers.rules.condition_spec import AlarmConditionSpecSerializer
from alarms.serializers.rules.device_profile_alarm import DeviceProfileAlarmSerializer, validate_profile_alarms
from alarms.serializers.rules.dynamic_value import DynamicValueSerializer
from alarms.serializers.rules.predicate import KeyFilterPredicateSerializer
from alarms.serializers.rules.predicate_value import FilterPredicateValueSerializer
from alarms.serializers.rules.schedule import AlarmScheduleSerializer

__all__ = [
    "AlarmConditionFilterKeySerializer",
    "AlarmConditionFilterSerializer",
    "AlarmConditionSerializer",
    "AlarmConditionSpecSerializer",
    "AlarmRuleSerializer",
    "AlarmScheduleSerializer",
    "DeviceProfileAlarmSerializer",
    "DynamicValueSerializer",
    "FilterPredicateValueSerializer",
    "KeyFilterPredicateSerializer",
    "validate_profile_alarms",
]

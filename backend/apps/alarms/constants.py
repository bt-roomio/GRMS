"""
The ThingsBoard alarm-rule vocabulary, ported verbatim.

Names and values match the TB classes one for one (``AlarmSeverity``,
``AlarmConditionKeyType``, ``EntityKeyValueType``, ``FilterPredicateType``,
``AlarmConditionSpecType``, ``AlarmScheduleType``, ``DynamicValueSourceType``),
so a rule exported from a TB device profile can be posted to
``/api/v1/alarms/rules/`` unchanged.
"""

from django.db import models


class AlarmSeverity(models.TextChoices):
    CRITICAL = "CRITICAL", "Critical"
    MAJOR = "MAJOR", "Major"
    MINOR = "MINOR", "Minor"
    WARNING = "WARNING", "Warning"
    INDETERMINATE = "INDETERMINATE", "Indeterminate"


# Most severe first: create rules are probed in this order and the first match wins.
SEVERITY_ORDER = (
    AlarmSeverity.CRITICAL,
    AlarmSeverity.MAJOR,
    AlarmSeverity.MINOR,
    AlarmSeverity.WARNING,
    AlarmSeverity.INDETERMINATE,
)

SEVERITY_RANK = {severity: rank for rank, severity in enumerate(SEVERITY_ORDER)}


class AlarmStatus(models.TextChoices):
    """Derived from the ``cleared``/``acknowledged`` pair, never stored."""

    ACTIVE_UNACK = "ACTIVE_UNACK", "Active unacknowledged"
    ACTIVE_ACK = "ACTIVE_ACK", "Active acknowledged"
    CLEARED_UNACK = "CLEARED_UNACK", "Cleared unacknowledged"
    CLEARED_ACK = "CLEARED_ACK", "Cleared acknowledged"


# AlarmConditionKeyType
KEY_TIME_SERIES = "TIME_SERIES"
KEY_ATTRIBUTE = "ATTRIBUTE"
KEY_ENTITY_FIELD = "ENTITY_FIELD"
KEY_CONSTANT = "CONSTANT"
KEY_TYPES = (KEY_TIME_SERIES, KEY_ATTRIBUTE, KEY_ENTITY_FIELD, KEY_CONSTANT)

# EntityKeyValueType
VALUE_STRING = "STRING"
VALUE_NUMERIC = "NUMERIC"
VALUE_BOOLEAN = "BOOLEAN"
VALUE_DATE_TIME = "DATE_TIME"
VALUE_TYPES = (VALUE_STRING, VALUE_NUMERIC, VALUE_BOOLEAN, VALUE_DATE_TIME)

# FilterPredicateType
PREDICATE_STRING = "STRING"
PREDICATE_NUMERIC = "NUMERIC"
PREDICATE_BOOLEAN = "BOOLEAN"
PREDICATE_COMPLEX = "COMPLEX"
PREDICATE_TYPES = (PREDICATE_STRING, PREDICATE_NUMERIC, PREDICATE_BOOLEAN, PREDICATE_COMPLEX)

# A DATE_TIME key is a millisecond epoch, so it is compared as a number.
VALUE_TYPE_TO_PREDICATE = {
    VALUE_STRING: PREDICATE_STRING,
    VALUE_NUMERIC: PREDICATE_NUMERIC,
    VALUE_BOOLEAN: PREDICATE_BOOLEAN,
    VALUE_DATE_TIME: PREDICATE_NUMERIC,
}

NUMERIC_OPERATIONS = ("EQUAL", "NOT_EQUAL", "GREATER", "LESS", "GREATER_OR_EQUAL", "LESS_OR_EQUAL")
BOOLEAN_OPERATIONS = ("EQUAL", "NOT_EQUAL")
STRING_OPERATIONS = ("EQUAL", "NOT_EQUAL", "STARTS_WITH", "ENDS_WITH", "CONTAINS", "NOT_CONTAINS", "IN", "NOT_IN")
COMPLEX_OPERATIONS = ("AND", "OR")

# AlarmConditionSpecType
SPEC_SIMPLE = "SIMPLE"
SPEC_DURATION = "DURATION"
SPEC_REPEATING = "REPEATING"
SPEC_TYPES = (SPEC_SIMPLE, SPEC_DURATION, SPEC_REPEATING)

TIME_UNITS = ("SECONDS", "MINUTES", "HOURS", "DAYS")
TIME_UNIT_SECONDS = {"SECONDS": 1, "MINUTES": 60, "HOURS": 3600, "DAYS": 86400}

# AlarmScheduleType
SCHEDULE_ANY_TIME = "ANY_TIME"
SCHEDULE_SPECIFIC_TIME = "SPECIFIC_TIME"
SCHEDULE_CUSTOM = "CUSTOM"
SCHEDULE_TYPES = (SCHEDULE_ANY_TIME, SCHEDULE_SPECIFIC_TIME, SCHEDULE_CUSTOM)

# DynamicValueSourceType.
# GRMS deviation: TB has CURRENT_USER (dropped — a rule has no user) and
# CURRENT_CUSTOMER (dropped — the Customer table is not maintained in GRMS, so a
# threshold set there would silently never resolve). CURRENT_ROOM is added
# instead, because the room is the level thresholds are set on in a hotel.
SOURCE_CURRENT_DEVICE = "CURRENT_DEVICE"
SOURCE_CURRENT_ROOM = "CURRENT_ROOM"
SOURCE_CURRENT_TENANT = "CURRENT_TENANT"
DYNAMIC_SOURCE_TYPES = (
    SOURCE_CURRENT_DEVICE,
    SOURCE_CURRENT_ROOM,
    SOURCE_CURRENT_TENANT,
)

# ``inherit`` walks this chain from the source upwards.
INHERIT_CHAIN = (
    SOURCE_CURRENT_DEVICE,
    SOURCE_CURRENT_ROOM,
    SOURCE_CURRENT_TENANT,
)

# GRMS deviation: TB resolves any entity field. Here it is a whitelist over
# ``Device`` (plus a few room fields) — everything else is rejected by the
# validator, so a rule can never reach into an unrelated column.
ENTITY_FIELD_WHITELIST = (
    "name",
    "type",
    "label",
    "status",
    "is_active",
    # GRMS extension: a gateway is not a separate profile here, it is a device
    # with additional_info["gateway"]. Exposing it as a field is what lets one
    # rule target gateways and another target everything else.
    "is_gateway",
    "room.number",
    "room.floor",
    "room.state",
)

# A crooked COMPLEX predicate must not be able to walk the evaluator into
# recursion; enforced by the validator and again at evaluation time.
MAX_COMPLEX_DEPTH = 5

# Server-scope attribute keys the connectivity rules lean on. ``notifyOnOffline``
# and ``gatewayActive`` are written by the device API and by the watchdog; the
# rules that read them are written by each tenant (see docs/alarms.md).
ATTR_ACTIVE = "active"
ATTR_NOTIFY_ON_OFFLINE = "notifyOnOffline"
ATTR_GATEWAY_ACTIVE = "gatewayActive"

# Where a tenant keeps overrides a DynamicValue can point at.
ATTRIBUTES_KEY = "attributes"

"""
The rule templates the panel offers in its "add a typical rule" menu.

Nothing here is seeded: a tenant starts with no rules and picks a template when
it wants one. Keeping the catalogue in the product code — rather than in the
tests, or hardcoded in the front end — means the rules the UI offers, the rules
docs/alarms.md describes and the rules the tests validate are the same objects.

``requires`` lists the keys a template leans on, so the builder can cross-check
them against ``/api/v1/alarms/available-keys/`` and grey out a template whose
telemetry this tenant never reports — a rule on a key nobody sends can never
fire, and that is invisible otherwise.
"""

from alarms.constants import (
    ATTR_ACTIVE,
    ATTR_GATEWAY_ACTIVE,
    ATTR_NOTIFY_ON_OFFLINE,
    AlarmSeverity,
)
from shuttle.constants import Room_Temperature

DEVICE_OFFLINE_MINUTES = 10
GATEWAY_OFFLINE_MINUTES = 5
TEMPERATURE_MINUTES = 5

# Hysteresis in the TB format is simply a gap between the raise and the clear
# threshold; there is no separate field for it.
HIGH_TEMPERATURE_ON = 30
HIGH_TEMPERATURE_OFF = 29
LOW_TEMPERATURE_ON = 16
LOW_TEMPERATURE_OFF = 17

ROOM_MAX_ATTRIBUTE = "temperatureMax"
ROOM_MIN_ATTRIBUTE = "temperatureMin"


# --------------------------------------------------------------------------
# Building blocks
# --------------------------------------------------------------------------


def boolean_filter(key: str, expected: bool, key_type: str = "ATTRIBUTE") -> dict:
    return {
        "key": {"type": key_type, "key": key},
        "valueType": "BOOLEAN",
        "predicate": {"type": "BOOLEAN", "operation": "EQUAL", "value": {"defaultValue": expected}},
    }


def numeric_filter(key: str, operation: str, default: float, attribute: str | None = None) -> dict:
    value: dict = {"defaultValue": default}
    if attribute:
        # "35 everywhere, 26 in room 512" expressed without a branch anywhere in
        # the evaluator.
        value["dynamicValue"] = {"sourceType": "CURRENT_ROOM", "sourceAttribute": attribute, "inherit": True}

    return {
        "key": {"type": "TIME_SERIES", "key": key},
        "valueType": "NUMERIC",
        "predicate": {"type": "NUMERIC", "operation": operation, "value": value},
    }


def duration(minutes: int) -> dict:
    return {"type": "DURATION", "unit": "MINUTES", "predicate": {"defaultValue": minutes}}


def simple_clear_rule(condition: list[dict]) -> dict:
    return {"condition": {"condition": condition, "spec": {"type": "SIMPLE"}}}


# --------------------------------------------------------------------------
# Templates
# --------------------------------------------------------------------------


def device_offline_rule(minutes: int = DEVICE_OFFLINE_MINUTES, severity: str = AlarmSeverity.MAJOR) -> dict:
    """
    Connectivity of an ordinary device.

    Carries the two guards that keep the journal readable: the per-device
    notification toggle, and ``gatewayActive`` — without the latter a dead
    gateway raises one alarm per device behind it instead of one of its own.
    """
    return {
        "alarmType": "Device Offline",
        "createRules": {
            severity: {
                "condition": {
                    "condition": [
                        boolean_filter(ATTR_ACTIVE, False),
                        boolean_filter(ATTR_NOTIFY_ON_OFFLINE, True),
                        boolean_filter(ATTR_GATEWAY_ACTIVE, True),
                        boolean_filter("is_gateway", False, key_type="ENTITY_FIELD"),
                    ],
                    "spec": duration(minutes),
                },
                "schedule": {"type": "ANY_TIME"},
                "alarmDetails": "Устройство ${originatorName} не на связи",
            }
        },
        "clearRule": simple_clear_rule([boolean_filter(ATTR_ACTIVE, True)]),
    }


def gateway_offline_rule(minutes: int = GATEWAY_OFFLINE_MINUTES, severity: str = AlarmSeverity.CRITICAL) -> dict:
    """The other half of the pair: gateways only, propagated to their devices."""
    return {
        "alarmType": "Gateway Offline",
        "createRules": {
            severity: {
                "condition": {
                    "condition": [
                        boolean_filter(ATTR_ACTIVE, False),
                        boolean_filter("is_gateway", True, key_type="ENTITY_FIELD"),
                    ],
                    "spec": duration(minutes),
                },
                "schedule": {"type": "ANY_TIME"},
                "alarmDetails": "Шлюз ${originatorName} не на связи",
            }
        },
        "clearRule": simple_clear_rule([boolean_filter(ATTR_ACTIVE, True)]),
        # One incident, visible on every device behind the gateway.
        "propagate": True,
    }


def high_temperature_rule(severity: str = AlarmSeverity.MINOR) -> dict:
    return {
        "alarmType": "High Temperature",
        "createRules": {
            severity: {
                "condition": {
                    "condition": [numeric_filter(Room_Temperature, "GREATER", HIGH_TEMPERATURE_ON, ROOM_MAX_ATTRIBUTE)],
                    "spec": duration(TEMPERATURE_MINUTES),
                },
                "schedule": {"type": "ANY_TIME"},
                "alarmDetails": "Температура ${Room Temperature}° в номере ${room}",
            }
        },
        "clearRule": simple_clear_rule([numeric_filter(Room_Temperature, "LESS", HIGH_TEMPERATURE_OFF)]),
    }


def low_temperature_rule(severity: str = AlarmSeverity.MINOR) -> dict:
    return {
        "alarmType": "Low Temperature",
        "createRules": {
            severity: {
                "condition": {
                    "condition": [numeric_filter(Room_Temperature, "LESS", LOW_TEMPERATURE_ON, ROOM_MIN_ATTRIBUTE)],
                    "spec": duration(TEMPERATURE_MINUTES),
                },
                "schedule": {"type": "ANY_TIME"},
                "alarmDetails": "Температура ${Room Temperature}° в номере ${room}",
            }
        },
        "clearRule": simple_clear_rule([numeric_filter(Room_Temperature, "GREATER", LOW_TEMPERATURE_OFF)]),
    }


# ``rule`` is a builder, not a dict: every caller gets a fresh copy it may edit.
TEMPLATES: tuple[dict, ...] = (
    {
        "id": "device-offline",
        "name": "Устройство не на связи",
        "description": (
            f"Устройство молчит {DEVICE_OFFLINE_MINUTES} минут. Учитывает тумблер уведомлений "
            f"устройства и состояние его шлюза, поэтому падение шлюза не поднимает аварию на каждом "
            f"устройстве за ним."
        ),
        "requires": {
            "attributes": [ATTR_ACTIVE, ATTR_NOTIFY_ON_OFFLINE, ATTR_GATEWAY_ACTIVE],
            "timeseries": [],
        },
        "rule": device_offline_rule,
    },
    {
        "id": "gateway-offline",
        "name": "Шлюз не на связи",
        "description": (
            f"Шлюз молчит {GATEWAY_OFFLINE_MINUTES} минут. Авария видна в карточке каждого устройства за этим шлюзом."
        ),
        "requires": {"attributes": [ATTR_ACTIVE], "timeseries": []},
        "rule": gateway_offline_rule,
    },
    {
        "id": "high-temperature",
        "name": "Высокая температура",
        "description": (
            f"Температура выше {HIGH_TEMPERATURE_ON}° дольше {TEMPERATURE_MINUTES} минут. "
            f"Порог можно переопределить на номере атрибутом «{ROOM_MAX_ATTRIBUTE}»."
        ),
        "requires": {"attributes": [], "timeseries": [Room_Temperature]},
        "rule": high_temperature_rule,
    },
    {
        "id": "low-temperature",
        "name": "Низкая температура",
        "description": (
            f"Температура ниже {LOW_TEMPERATURE_ON}° дольше {TEMPERATURE_MINUTES} минут. "
            f"Порог можно переопределить на номере атрибутом «{ROOM_MIN_ATTRIBUTE}»."
        ),
        "requires": {"attributes": [], "timeseries": [Room_Temperature]},
        "rule": low_temperature_rule,
    },
)


def catalogue() -> list[dict]:
    """The templates with their rules materialised, ready to be serialised."""
    return [{**entry, "rule": entry["rule"]()} for entry in TEMPLATES]

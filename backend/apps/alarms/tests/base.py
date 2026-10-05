from django.test import TestCase

from alarms.constants import ATTR_ACTIVE, ATTR_GATEWAY_ACTIVE, ATTR_NOTIFY_ON_OFFLINE
from alarms.services.attributes import set_server_attribute
from main.models import DeviceProfile
from shuttle.models import TsKvDictionary, TsKvLatest

# From apps/main/fixtures.
TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"
OTHER_TENANT_ID = "5b2b6879-0791-4b14-8545-6abf61e73b68"
PROFILE_ID = "be17d30b-9785-4415-bfa5-e7fdaf19e37c"
DEVICE_ID = "47aef21b-6cc9-4ec5-8573-1a6f491940c0"
OTHER_DEVICE_ID = "a1561fb2-e031-42ce-812a-0ce84843c0f0"
FOREIGN_DEVICE_ID = "9829490d-f742-400e-8f38-aae5155e0b27"
ROOM_ID = "df77f910-2dcd-45cf-b6be-054c744561a7"


class AlarmTestCase(TestCase):
    """Shared scaffolding for the tests that need real rows."""

    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "customer.yaml",
        "room.yaml",
        "device_profile.yaml",
        "device.yaml",
    )

    def set_rules(self, *rules, profile_id=PROFILE_ID):
        profile = DeviceProfile.objects.get(pk=profile_id)
        profile_data = profile.profile_data if isinstance(profile.profile_data, dict) else {}
        profile.profile_data = {**profile_data, "alarms": list(rules)}
        # save() runs full_clean(), which the fixtures' duplicate profile names
        # would trip over; the rules are the only thing under test here.
        DeviceProfile.objects.filter(pk=profile.pk).update(profile_data=profile.profile_data)
        return profile

    def set_attribute(self, key, value, device_id=DEVICE_ID):
        return set_server_attribute(device_id, key, value)

    def set_telemetry(self, key, value, device_id=DEVICE_ID):
        dictionary, _ = TsKvDictionary.objects.get_or_create(key=key)
        column = "dbl_v" if isinstance(value, float) else "long_v"
        latest, _ = TsKvLatest.objects.update_or_create(
            entity_id=device_id,
            key_id=dictionary.key_id,
            defaults={column: value},
        )
        return latest


def boolean_filter(key, expected, key_type="ATTRIBUTE"):
    return {
        "key": {"type": key_type, "key": key},
        "valueType": "BOOLEAN",
        "predicate": {"type": "BOOLEAN", "operation": "EQUAL", "value": {"defaultValue": expected}},
    }


def offline_rule(minutes=10, severity="MAJOR", alarm_type="Device Offline", clear=True, **extra):
    """A minimal offline rule: connectivity only, without any of the guards."""
    rule = {
        "alarmType": alarm_type,
        "createRules": {
            severity: {
                "condition": {
                    "condition": [boolean_filter(ATTR_ACTIVE, False)],
                    "spec": {"type": "DURATION", "unit": "MINUTES", "predicate": {"defaultValue": minutes}}
                    if minutes
                    else {"type": "SIMPLE"},
                },
                "schedule": {"type": "ANY_TIME"},
                "alarmDetails": "Устройство ${originatorName} не на связи",
            }
        },
        **extra,
    }

    if clear:
        rule["clearRule"] = {
            "condition": {
                "condition": [boolean_filter(ATTR_ACTIVE, True)],
                "spec": {"type": "SIMPLE"},
            }
        }

    return rule


def guarded_offline_rule(minutes=10, severity="MAJOR"):
    """
    The device-offline rule as docs/alarms.md recommends assembling it: the
    per-device toggle and the gateway guard included, so a dead gateway raises
    one alarm instead of one per device behind it.
    """
    rule = offline_rule(minutes=minutes, severity=severity)
    rule["createRules"][severity]["condition"]["condition"] += [
        boolean_filter(ATTR_NOTIFY_ON_OFFLINE, True),
        boolean_filter(ATTR_GATEWAY_ACTIVE, True),
        boolean_filter("is_gateway", False, key_type="ENTITY_FIELD"),
    ]
    return rule


def gateway_offline_rule(minutes=5, severity="CRITICAL"):
    """The other half of the pair: gateways only, propagated to their devices."""
    rule = offline_rule(minutes=minutes, severity=severity, alarm_type="Gateway Offline", propagate=True)
    create_rule = rule["createRules"][severity]
    create_rule["condition"]["condition"].append(boolean_filter("is_gateway", True, key_type="ENTITY_FIELD"))
    create_rule["alarmDetails"] = "Шлюз ${originatorName} не на связи"
    return rule


def temperature_rule(threshold=30, severity="MINOR", attribute="temperatureMax"):
    value = {"defaultValue": threshold}
    if attribute:
        value["dynamicValue"] = {"sourceType": "CURRENT_ROOM", "sourceAttribute": attribute, "inherit": True}

    return {
        "alarmType": "High Temperature",
        "createRules": {
            severity: {
                "condition": {
                    "condition": [
                        {
                            "key": {"type": "TIME_SERIES", "key": "Room Temperature"},
                            "valueType": "NUMERIC",
                            "predicate": {"type": "NUMERIC", "operation": "GREATER", "value": value},
                        }
                    ],
                    "spec": {"type": "SIMPLE"},
                },
                "schedule": {"type": "ANY_TIME"},
                "alarmDetails": "Температура ${Room Temperature}° в номере ${room}",
            }
        },
    }

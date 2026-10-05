from django.test import TestCase

from alarms.constants import ATTR_ACTIVE
from alarms.models import AlarmRule
from alarms.services.attributes import set_server_attribute
from alarms.templates import boolean_filter
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

    def set_rules(self, *rules, profile_id=PROFILE_ID, enabled=True):
        """Give a profile exactly these rules, as rows — what the CRUD writes."""
        profile = DeviceProfile.objects.get(pk=profile_id)
        AlarmRule.objects.filter(device_profile=profile).delete()

        return [
            AlarmRule.objects.create(
                tenant_id=profile.tenant_id,
                device_profile=profile,
                alarm_type=rule["alarmType"],
                enabled=enabled,
                create_rules=rule.get("createRules") or {},
                clear_rule=rule.get("clearRule"),
                propagate=bool(rule.get("propagate")),
                propagate_relation_types=rule.get("propagateRelationTypes") or [],
                propagate_to_owner=bool(rule.get("propagateToOwner")),
                propagate_to_tenant=bool(rule.get("propagateToTenant")),
            )
            for rule in rules
        ]

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

from django.test import SimpleTestCase

from rest_framework.exceptions import ValidationError

from alarms.serializers.rules import DeviceProfileAlarmSerializer, validate_profile_alarms
from alarms.tests.factories import boolean, numeric, ts_filter


def alarm(filters=None, spec=None, alarm_type="High Temperature", severity="CRITICAL", **extra):
    return {
        "alarmType": alarm_type,
        "createRules": {
            severity: {
                "condition": {
                    "condition": filters or [ts_filter("Room Temperature", "NUMERIC", numeric("GREATER", 30))],
                    "spec": spec or {"type": "SIMPLE"},
                },
                "schedule": {"type": "ANY_TIME"},
                "alarmDetails": "hot",
            }
        },
        **extra,
    }


class RuleValidationTest(SimpleTestCase):
    def assert_invalid(self, payload):
        serializer = DeviceProfileAlarmSerializer(data=payload)
        self.assertFalse(serializer.is_valid(), serializer.validated_data)
        return serializer.errors

    def test_a_well_formed_rule_survives_unchanged(self):
        serializer = DeviceProfileAlarmSerializer(data=alarm())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        # camelCase in, camelCase out: the rule can go back into profile_data
        # exactly as ThingsBoard would have written it.
        self.assertEqual(serializer.validated_data["alarmType"], "High Temperature")
        self.assertIn("CRITICAL", serializer.validated_data["createRules"])

    def test_empty_create_rules(self):
        payload = alarm()
        payload["createRules"] = {}
        self.assert_invalid(payload)

    def test_unknown_severity(self):
        self.assert_invalid(alarm(severity="URGENT"))

    def test_value_type_must_match_the_predicate_type(self):
        self.assert_invalid(alarm(filters=[ts_filter("Room Temperature", "BOOLEAN", numeric("GREATER", 30))]))

    def test_complex_children_must_match_the_value_type_too(self):
        mixed = {"type": "COMPLEX", "operation": "OR", "predicates": [numeric("GREATER", 30), boolean("EQUAL", True)]}
        self.assert_invalid(alarm(filters=[ts_filter("Room Temperature", "NUMERIC", mixed)]))

    def test_complex_depth_cap(self):
        predicate = numeric("GREATER", 30)
        for _ in range(6):
            predicate = {"type": "COMPLEX", "operation": "AND", "predicates": [predicate]}
        self.assert_invalid(alarm(filters=[ts_filter("Room Temperature", "NUMERIC", predicate)]))

    def test_entity_field_whitelist(self):
        allowed = {
            "key": {"type": "ENTITY_FIELD", "key": "is_gateway"},
            "valueType": "BOOLEAN",
            "predicate": boolean("EQUAL", True),
        }
        serializer = DeviceProfileAlarmSerializer(data=alarm(filters=[allowed]))
        self.assertTrue(serializer.is_valid(), serializer.errors)

        forbidden = {**allowed, "key": {"type": "ENTITY_FIELD", "key": "device_data"}}
        self.assert_invalid(alarm(filters=[forbidden]))

    def test_constant_key_needs_a_value(self):
        self.assert_invalid(
            alarm(filters=[{"key": {"type": "CONSTANT"}, "valueType": "NUMERIC", "predicate": numeric("GREATER", 1)}])
        )

    def test_non_constant_key_needs_a_name(self):
        self.assert_invalid(alarm(filters=[ts_filter("", "NUMERIC", numeric("GREATER", 30))]))

    def test_predicate_value_needs_a_default_or_a_dynamic_value(self):
        self.assert_invalid(alarm(filters=[ts_filter("Room Temperature", "NUMERIC", numeric("GREATER", None))]))

    def test_duration_spec_requires_a_positive_value(self):
        spec = {"type": "DURATION", "unit": "MINUTES", "predicate": {"defaultValue": 0}}
        self.assert_invalid(alarm(spec=spec))

        spec = {"type": "DURATION", "predicate": {"defaultValue": 5}}
        self.assert_invalid(alarm(spec=spec))

    def test_repeating_spec_requires_an_integer_count(self):
        self.assert_invalid(alarm(spec={"type": "REPEATING", "predicate": {"defaultValue": 0}}))

    def test_unknown_dynamic_source(self):
        predicate = numeric(
            "GREATER",
            30,
            dynamic={"sourceType": "CURRENT_ASSET", "sourceAttribute": "temperatureMax"},
        )
        self.assert_invalid(alarm(filters=[ts_filter("Room Temperature", "NUMERIC", predicate)]))

    def test_current_room_source_is_accepted(self):
        predicate = numeric(
            "GREATER",
            30,
            dynamic={"sourceType": "CURRENT_ROOM", "sourceAttribute": "temperatureMax", "inherit": True},
        )
        serializer = DeviceProfileAlarmSerializer(
            data=alarm(filters=[ts_filter("Room Temperature", "NUMERIC", predicate)])
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_bad_schedule_timezone(self):
        payload = alarm()
        payload["createRules"]["CRITICAL"]["schedule"] = {
            "type": "SPECIFIC_TIME",
            "timezone": "Mars/Olympus",
            "daysOfWeek": [1],
            "startsOn": 0,
            "endsOn": 1000,
        }
        self.assert_invalid(payload)


class ProfileAlarmsTest(SimpleTestCase):
    def test_duplicate_alarm_types_are_rejected(self):
        with self.assertRaises(ValidationError):
            validate_profile_alarms([alarm(), alarm()])

    def test_empty_and_null_lists(self):
        self.assertEqual(validate_profile_alarms(None), [])
        self.assertEqual(validate_profile_alarms([]), [])

    def test_a_non_list_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_profile_alarms({"alarmType": "x"})

    def test_documented_connectivity_rules_pass_the_validator(self):
        from alarms.tests.base import gateway_offline_rule, guarded_offline_rule

        self.assertEqual(len(validate_profile_alarms([guarded_offline_rule(), gateway_offline_rule()])), 2)

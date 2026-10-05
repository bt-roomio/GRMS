from django.test import SimpleTestCase

from alarms.services.details import matched_values, render
from alarms.tests.factories import numeric, snapshot, ts_filter


class DetailsTemplateTest(SimpleTestCase):
    def setUp(self):
        self.snapshot = snapshot(ts={"Room Temperature": 31.5}, attrs={"active": False})

    def test_placeholders_with_spaces_in_the_key(self):
        text = render("Температура ${Room Temperature}° в номере ${room}", self.snapshot, "High Temperature", "MINOR")
        self.assertEqual(text, "Температура 31.5° в номере 101")

    def test_service_placeholders(self):
        text = render("${alarmType}/${alarmSeverity}: ${originatorName}", self.snapshot, "High Temperature", "MINOR")
        self.assertEqual(text, "High Temperature/MINOR: Thermostat 101")

    def test_unknown_placeholder_is_left_alone(self):
        # A typo in a rule must not take the evaluator down mid-tick.
        text = render("${Nope} and ${room}", self.snapshot, "High Temperature", "MINOR")
        self.assertEqual(text, "${Nope} and 101")

    def test_empty_template_falls_back_to_the_type_and_device(self):
        self.assertEqual(render(None, self.snapshot, "Device Offline", "MAJOR"), "Device Offline — Thermostat 101")

    def test_attribute_values_are_reachable(self):
        self.assertEqual(render("${active}", self.snapshot, "Device Offline", "MAJOR"), "False")

    def test_matched_values_snapshot_skips_constants(self):
        filters = [
            ts_filter("Room Temperature", "NUMERIC", numeric("GREATER", 30)),
            {"key": {"type": "CONSTANT"}, "valueType": "NUMERIC", "value": 1, "predicate": numeric("GREATER", 0)},
        ]
        self.assertEqual(matched_values(filters, self.snapshot), {"Room Temperature": 31.5})

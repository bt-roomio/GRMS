from django.test import SimpleTestCase

from alarms.services.dynamic import resolve_value
from alarms.tests.factories import snapshot


def dynamic(source_type, attribute="temperatureMax", inherit=False):
    return {
        "defaultValue": 35,
        "dynamicValue": {"sourceType": source_type, "sourceAttribute": attribute, "inherit": inherit},
    }


class DynamicValueTest(SimpleTestCase):
    def test_default_value_is_used_without_a_dynamic_value(self):
        self.assertEqual(resolve_value({"defaultValue": 30}, snapshot(), "NUMERIC"), 30.0)

    def test_room_attribute_overrides_the_default(self):
        data = snapshot(room_attrs={"temperatureMax": 26})
        self.assertEqual(resolve_value(dynamic("CURRENT_ROOM"), data, "NUMERIC"), 26.0)

    def test_device_attribute_wins_over_the_room(self):
        data = snapshot(attrs={"temperatureMax": 22}, room_attrs={"temperatureMax": 26})
        self.assertEqual(resolve_value(dynamic("CURRENT_DEVICE"), data, "NUMERIC"), 22.0)

    def test_missing_attribute_falls_back_to_the_default(self):
        self.assertEqual(resolve_value(dynamic("CURRENT_ROOM"), snapshot(), "NUMERIC"), 35.0)

    def test_inherit_walks_device_room_tenant(self):
        data = snapshot(tenant_attrs={"temperatureMax": 28})
        self.assertEqual(resolve_value(dynamic("CURRENT_DEVICE", inherit=True), data, "NUMERIC"), 28.0)

        data = snapshot(room_attrs={"temperatureMax": 27}, tenant_attrs={"temperatureMax": 28})
        self.assertEqual(resolve_value(dynamic("CURRENT_DEVICE", inherit=True), data, "NUMERIC"), 27.0)

    def test_inherit_never_walks_downwards(self):
        # A tenant-scoped source must not pick up a room's value.
        data = snapshot(room_attrs={"temperatureMax": 26})
        self.assertEqual(resolve_value(dynamic("CURRENT_TENANT", inherit=True), data, "NUMERIC"), 35.0)

    def test_no_value_at_all(self):
        self.assertIsNone(resolve_value({"defaultValue": None}, snapshot(), "NUMERIC"))
        self.assertIsNone(resolve_value(None, snapshot(), "NUMERIC"))

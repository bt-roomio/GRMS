from django.test import SimpleTestCase

from alarms.services.predicates import eval_condition, eval_predicate
from alarms.tests.factories import attr_filter, boolean, numeric, snapshot, string, ts_filter


class NumericPredicateTest(SimpleTestCase):
    def setUp(self):
        self.snapshot = snapshot(ts={"Room Temperature": 24.5})

    def evaluate(self, operation, threshold, actual=24.5):
        return eval_predicate(numeric(operation, threshold), actual, self.snapshot, "NUMERIC")

    def test_every_operation(self):
        self.assertTrue(self.evaluate("GREATER", 20))
        self.assertFalse(self.evaluate("GREATER", 30))
        self.assertTrue(self.evaluate("LESS", 30))
        self.assertFalse(self.evaluate("LESS", 20))
        self.assertTrue(self.evaluate("EQUAL", 24.5))
        self.assertTrue(self.evaluate("NOT_EQUAL", 24.6))
        self.assertTrue(self.evaluate("GREATER_OR_EQUAL", 24.5))
        self.assertTrue(self.evaluate("LESS_OR_EQUAL", 24.5))

    def test_integer_telemetry_is_compared_as_a_number(self):
        # Some controllers publish into long_v; the reader has to bridge that.
        self.assertTrue(eval_predicate(numeric("GREATER", 20), 24, self.snapshot, "NUMERIC"))

    def test_missing_value_never_matches(self):
        # Not even NOT_EQUAL: a device that never reported must stay quiet.
        self.assertFalse(eval_predicate(numeric("NOT_EQUAL", 1), None, self.snapshot, "NUMERIC"))

    def test_missing_threshold_never_matches(self):
        self.assertFalse(eval_predicate(numeric("GREATER", None), 24.5, self.snapshot, "NUMERIC"))


class BooleanPredicateTest(SimpleTestCase):
    def setUp(self):
        self.snapshot = snapshot(attrs={"active": False})

    def test_equal_and_not_equal(self):
        self.assertTrue(eval_predicate(boolean("EQUAL", False), False, self.snapshot, "BOOLEAN"))
        self.assertFalse(eval_predicate(boolean("EQUAL", True), False, self.snapshot, "BOOLEAN"))
        self.assertTrue(eval_predicate(boolean("NOT_EQUAL", True), False, self.snapshot, "BOOLEAN"))

    def test_string_booleans_are_coerced(self):
        self.assertTrue(eval_predicate(boolean("EQUAL", True), "true", self.snapshot, "BOOLEAN"))


class StringPredicateTest(SimpleTestCase):
    def setUp(self):
        self.snapshot = snapshot()

    def evaluate(self, predicate, actual="Thermostat 101"):
        return eval_predicate(predicate, actual, self.snapshot, "STRING")

    def test_every_operation(self):
        self.assertTrue(self.evaluate(string("EQUAL", "Thermostat 101")))
        self.assertTrue(self.evaluate(string("NOT_EQUAL", "Other")))
        self.assertTrue(self.evaluate(string("STARTS_WITH", "Thermo")))
        self.assertTrue(self.evaluate(string("ENDS_WITH", "101")))
        self.assertTrue(self.evaluate(string("CONTAINS", "mostat")))
        self.assertTrue(self.evaluate(string("NOT_CONTAINS", "zzz")))

    def test_ignore_case(self):
        self.assertFalse(self.evaluate(string("EQUAL", "thermostat 101")))
        self.assertTrue(self.evaluate(string("EQUAL", "thermostat 101", ignore_case=True)))

    def test_in_accepts_a_list_and_a_csv_string(self):
        self.assertTrue(self.evaluate(string("IN", ["Thermostat 101", "Other"])))
        self.assertTrue(self.evaluate(string("IN", "Other,Thermostat 101")))
        self.assertTrue(self.evaluate(string("NOT_IN", "Other,Another")))


class ComplexPredicateTest(SimpleTestCase):
    def setUp(self):
        self.snapshot = snapshot(ts={"Room Temperature": 24.5})

    def complex_predicate(self, operation, *children):
        return {"type": "COMPLEX", "operation": operation, "predicates": list(children)}

    def test_or_matches_when_one_child_does(self):
        predicate = self.complex_predicate("OR", numeric("LESS", 10), numeric("GREATER", 20))
        self.assertTrue(eval_predicate(predicate, 24.5, self.snapshot, "NUMERIC"))

    def test_and_needs_every_child(self):
        predicate = self.complex_predicate("AND", numeric("GREATER", 20), numeric("LESS", 30))
        self.assertTrue(eval_predicate(predicate, 24.5, self.snapshot, "NUMERIC"))

        predicate = self.complex_predicate("AND", numeric("GREATER", 20), numeric("LESS", 24))
        self.assertFalse(eval_predicate(predicate, 24.5, self.snapshot, "NUMERIC"))

    def test_nesting(self):
        inner = self.complex_predicate("AND", numeric("GREATER", 20), numeric("LESS", 30))
        outer = self.complex_predicate("OR", numeric("EQUAL", 0), inner)
        self.assertTrue(eval_predicate(outer, 24.5, self.snapshot, "NUMERIC"))

    def test_depth_cap_stops_runaway_nesting(self):
        predicate = numeric("GREATER", 20)
        for _ in range(8):
            predicate = self.complex_predicate("AND", predicate)
        self.assertFalse(eval_predicate(predicate, 24.5, self.snapshot, "NUMERIC"))


class ConditionTest(SimpleTestCase):
    def test_filters_are_anded(self):
        data = snapshot(ts={"Room Temperature": 31.0}, attrs={"active": True})
        filters = [
            ts_filter("Room Temperature", "NUMERIC", numeric("GREATER", 30)),
            attr_filter("active", "BOOLEAN", boolean("EQUAL", True)),
        ]
        self.assertTrue(eval_condition(filters, data))

        filters[1] = attr_filter("active", "BOOLEAN", boolean("EQUAL", False))
        self.assertFalse(eval_condition(filters, data))

    def test_empty_condition_never_matches(self):
        self.assertFalse(eval_condition([], snapshot()))

    def test_entity_field_and_constant_keys(self):
        data = snapshot(fields={"is_gateway": True})
        entity = {
            "key": {"type": "ENTITY_FIELD", "key": "is_gateway"},
            "valueType": "BOOLEAN",
            "predicate": boolean("EQUAL", True),
        }
        constant = {
            "key": {"type": "CONSTANT"},
            "valueType": "NUMERIC",
            "value": 5,
            "predicate": numeric("GREATER", 1),
        }
        self.assertTrue(eval_condition([entity, constant], data))

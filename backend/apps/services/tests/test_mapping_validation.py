from django.test import SimpleTestCase

from services.mapping.validation import rule_errors


def rule(transform, value_type="integer", **fields):
    return {"tag_name": "tag", "external": {"value_type": value_type}, "transform": transform, **fields}


def enum(*pairs):
    return {"type": "enum", "map": [{"grms": grms, "external": external} for grms, external in pairs]}


class RuleErrorsTest(SimpleTestCase):
    def assert_valid(self, mapping_rule):
        self.assertEqual(rule_errors(mapping_rule), [])

    def assert_invalid(self, mapping_rule, fragment):
        errors = rule_errors(mapping_rule)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_valid_rules(self):
        self.assert_valid(rule(enum(("Low", 1), ("High", 3))))
        self.assert_valid(
            rule(
                {"type": "range", "grms": {"min": 0, "max": 255}, "external": {"min": 0, "max": 100, "step": 10}},
                on_invalid="clamp",
            )
        )
        self.assert_valid(rule({"type": "linear", "ops": [{"op": "divide", "value": 10}]}, value_type="number"))
        self.assert_valid(rule({"type": "passthrough"}, value_type="string"))

    def test_identity_and_vocabulary(self):
        self.assert_invalid({**rule({"type": "passthrough"}), "tag_name": None}, "tag_name must be")
        self.assert_invalid(rule({"type": "passthrough"}, value_type="float"), "value_type")
        self.assert_invalid(rule({"type": "passthrough"}, direction="sideways"), "direction")
        self.assert_invalid(rule({"type": "passthrough"}, on_invalid="ignore"), "on_invalid")
        self.assert_invalid(rule({"type": "formula"}), "transform.type")
        self.assertEqual(rule_errors([]), ["A rule must be an object."])

    def test_enum_must_be_unambiguous_both_ways(self):
        self.assert_invalid(rule(enum(("Low", 1), ("Slow", 1))), "a write would be ambiguous")
        self.assert_invalid(rule(enum(("Low", 1), ("Low", 2))), "a read would be ambiguous")

    def test_enum_one_way_allows_duplicates_on_the_other_side(self):
        # Reads only: two GRMS values may show as the same external value.
        self.assert_valid(rule(enum(("Off", 0), ("Standby", 0)), direction="to_external"))

    def test_enum_external_values_match_value_type(self):
        self.assert_invalid(rule(enum(("Low", "1"))), "are not integer")
        self.assert_invalid(rule(enum((True, 1))) | {"transform": {"type": "enum", "map": []}}, "non-empty")
        self.assert_invalid(rule({"type": "enum", "map": [{"grms": 1}]}), "must have grms and external")

    def test_range_bounds(self):
        bad = {"type": "range", "grms": {"min": 10, "max": 10}, "external": {"min": 0, "max": 100, "step": 0}}
        self.assert_invalid(rule(bad), "transform.grms.min must be less")
        self.assert_invalid(rule(bad), "transform.external.step must be a positive")
        self.assert_invalid(rule({"type": "range", "grms": {"min": 0}, "external": None}), "must be numbers")

    def test_numeric_transform_needs_numeric_type(self):
        transform = {"type": "linear", "ops": [{"op": "add", "value": 1}]}
        self.assert_invalid(rule(transform, value_type="string"), "numeric external value_type")

    def test_linear_ops(self):
        self.assert_invalid(rule({"type": "linear", "ops": [{"op": "divide", "value": 0}]}), "divide by 0")
        self.assert_invalid(rule({"type": "linear", "ops": [{"op": "multiply", "value": 0}]}), "multiply by 0")
        self.assert_invalid(rule({"type": "linear", "ops": [{"op": "power", "value": 2}]}), "op must be one of")
        self.assert_invalid(rule({"type": "linear", "ops": []}), "non-empty list")

    def test_clamp_needs_numbers(self):
        self.assert_invalid(rule(enum(("on", "1")), value_type="string", on_invalid="clamp"), "clamp")

    def test_const_needs_its_value(self):
        passthrough = {"type": "passthrough"}
        self.assert_valid(rule(passthrough, on_invalid="const", on_invalid_value=0))
        self.assert_invalid(rule(passthrough, on_invalid="const"), "needs on_invalid_value")
        self.assert_invalid(rule(passthrough, on_invalid_value=0), "only with on_invalid const")

import copy

from django.test import SimpleTestCase

from services.mapping import composite
from services.mapping.composite import AMBIGUOUS, composite_rule_issues, composite_rules_issues
from services.mapping.engine import SKIP, MappingError

FCU_MODE = {
    "id": "fcumode",
    "output": {"tag_name": "fcumode", "value_type": "integer"},
    "inputs": [
        {"alias": "power", "tag_name": "AC ON OFF", "source": "attribute"},
        {"alias": "mode", "tag_name": "AC Mode", "source": "attribute"},
    ],
    "conditions": [
        {"when": {"power": 0}, "value": 0},
        {"when": {"power": 1, "mode": "Heat"}, "value": 1},
        {"when": {"power": 1, "mode": "Cool"}, "value": 2},
    ],
    "actions": [
        {"value": 0, "set": [{"alias": "power", "value": 0}]},
        {"value": 1, "set": [{"alias": "mode", "value": "Heat"}, {"alias": "power", "value": 1}]},
        {"value": 2, "set": [{"alias": "mode", "value": "Cool"}, {"alias": "power", "value": 1}]},
    ],
}


def fcu_mode(**fields):
    return {**copy.deepcopy(FCU_MODE), **fields}


def fields(issues):
    return [issue.field for issue in issues]


class CompositeReadTest(SimpleTestCase):
    def test_conditions_table(self):
        self.assertEqual(composite.to_external(FCU_MODE, {"power": 0, "mode": "Cool"}), 0)
        self.assertEqual(composite.to_external(FCU_MODE, {"power": 1, "mode": "Heat"}), 1)
        self.assertEqual(composite.to_external(FCU_MODE, {"power": 1, "mode": "Cool"}), 2)

    def test_input_the_result_does_not_depend_on_may_be_missing(self):
        self.assertEqual(composite.to_external(FCU_MODE, {"power": 0}), 0)
        self.assertEqual(composite.to_external(FCU_MODE, {"power": 0}, {"mode": AMBIGUOUS}), 0)

    def test_missing_input_skips_by_default(self):
        self.assertIs(composite.to_external(FCU_MODE, {"power": 1}), SKIP)

    def test_missing_input_rejected(self):
        with self.assertRaises(MappingError) as caught:
            composite.to_external(fcu_mode(on_missing="reject"), {"power": 1}, {"mode": AMBIGUOUS})
        self.assertEqual(caught.exception.code, AMBIGUOUS)
        self.assertEqual(caught.exception.field, "inputs.mode")

    def test_no_match(self):
        with self.assertRaises(MappingError) as caught:
            composite.to_external(FCU_MODE, {"power": 1, "mode": "Fan"})
        self.assertEqual(caught.exception.code, "unmapped")
        self.assertIs(composite.to_external(fcu_mode(on_no_match="skip"), {"power": 1, "mode": "Fan"}), SKIP)
        rule = fcu_mode(on_no_match="const", default_value=0)
        self.assertEqual(composite.to_external(rule, {"power": 1, "mode": "Fan"}), 0)

    def test_constraints(self):
        rule = fcu_mode(
            conditions=[
                {"when": {"power": {"in": [0, False]}}, "value": 0},
                {"when": {"power": {"in": [1, True]}, "mode": {"min": 10, "max": 20}}, "value": 1},
            ],
            direction="to_external",
            actions=None,
        )
        self.assertEqual(composite.to_external(rule, {"power": False}), 0)
        self.assertEqual(composite.to_external(rule, {"power": True, "mode": "15"}), 1)

    def test_direction(self):
        with self.assertRaises(MappingError) as caught:
            composite.to_external(fcu_mode(direction="to_grms"), {"power": 0})
        self.assertEqual(caught.exception.code, "direction")


class CompositeWriteTest(SimpleTestCase):
    def test_actions_in_order(self):
        writes = composite.to_grms(FCU_MODE, 2)
        self.assertEqual([(w["tag_name"], w["value"]) for w in writes], [("AC Mode", "Cool"), ("AC ON OFF", 1)])
        self.assertTrue(all(w["required"] for w in writes))

    def test_value_is_coerced(self):
        self.assertEqual(len(composite.to_grms(FCU_MODE, "1")), 2)

    def test_unknown_value(self):
        with self.assertRaises(MappingError) as caught:
            composite.to_grms(FCU_MODE, 7)
        self.assertEqual(caught.exception.code, "unmapped")
        self.assertIs(composite.to_grms(fcu_mode(on_no_match="skip"), 7), SKIP)

    def test_wrong_type(self):
        with self.assertRaises(MappingError) as caught:
            composite.to_grms(FCU_MODE, "cool")
        self.assertEqual(caught.exception.code, "type")

    def test_output_ranges(self):
        self.assertEqual(composite.output_ranges(FCU_MODE), [0, 1, 2])
        self.assertEqual(
            composite.output_ranges(fcu_mode(output={**FCU_MODE["output"], "tag_ranges": ["0-2"]})), ["0-2"]
        )


class CompositeValidationTest(SimpleTestCase):
    def test_valid(self):
        self.assertEqual(composite_rule_issues(FCU_MODE), [])

    def test_unknown_alias_in_condition(self):
        rule = fcu_mode()
        rule["conditions"][1]["when"]["speed"] = 1
        self.assertIn("conditions[1].when.speed", fields(composite_rule_issues(rule)))

    def test_repeated_alias(self):
        rule = fcu_mode()
        rule["inputs"][1]["alias"] = "power"
        self.assertEqual(fields(composite_rule_issues(rule)), ["inputs"])

    def test_overlapping_conditions_conflict(self):
        rule = fcu_mode()
        rule["conditions"].append({"when": {"mode": "Cool"}, "value": 1})
        issues = composite_rule_issues(rule)
        self.assertEqual(
            [(i.field, i.code) for i in issues], [("conditions[3]", "conflict"), ("conditions[3]", "conflict")]
        )

    def test_overlapping_conditions_with_one_value_are_allowed(self):
        rule = fcu_mode()
        rule["conditions"].append({"when": {"power": {"in": [0, 2]}}, "value": 0})
        self.assertEqual(composite_rule_issues(rule), [])

    def test_interval_overlap(self):
        rule = fcu_mode(direction="to_external", actions=None)
        rule["conditions"] = [{"when": {"power": {"min": 0, "max": 5}}, "value": 0}, {"when": {"power": 5}, "value": 1}]
        self.assertEqual([i.code for i in composite_rule_issues(rule)], ["conflict"])

    def test_action_that_reads_back_as_another_value(self):
        rule = fcu_mode()
        rule["actions"][2]["set"][0]["value"] = "Heat"
        self.assertEqual([(i.field, i.code) for i in composite_rule_issues(rule)], [("actions[2]", "conflict")])

    def test_wrong_value_types(self):
        rule = fcu_mode()
        rule["conditions"][0]["value"] = "off"
        rule["actions"][0]["value"] = 0.5
        self.assertEqual(fields(composite_rule_issues(rule)), ["conditions[0].value", "actions[0].value"])

    def test_values_outside_output_ranges(self):
        rule = fcu_mode(output={**FCU_MODE["output"], "tag_ranges": [0, 1]})
        self.assertEqual(fields(composite_rule_issues(rule)), ["conditions[2].value", "actions[2].value"])

    def test_repeated_action_value(self):
        rule = fcu_mode()
        rule["actions"][1]["value"] = 2
        self.assertIn("actions", fields(composite_rule_issues(rule)))

    def test_action_alias_must_be_an_input(self):
        rule = fcu_mode()
        rule["actions"][0]["set"][0]["alias"] = "fan"
        self.assertEqual(fields(composite_rule_issues(rule)), ["actions[0].set[0].alias"])

    def test_output_cannot_be_an_input(self):
        rule = fcu_mode(output={"tag_name": "AC Mode", "value_type": "integer"})
        self.assertEqual(fields(composite_rule_issues(rule)), ["output.tag_name"])

    def test_direction_needs_its_part(self):
        self.assertEqual(fields(composite_rule_issues(fcu_mode(conditions=[]))), ["conditions"])
        self.assertEqual(composite_rule_issues(fcu_mode(conditions=None, direction="to_grms")), [])

    def test_const_needs_reads_and_a_default(self):
        self.assertEqual(fields(composite_rule_issues(fcu_mode(on_no_match="const"))), ["default_value"])
        rule = fcu_mode(on_no_match="const", default_value=0, direction="to_grms")
        self.assertEqual(fields(composite_rule_issues(rule)), ["on_no_match"])

    def test_malformed(self):
        self.assertEqual(fields(composite_rule_issues([])), [""])
        self.assertEqual(fields(composite_rule_issues({"id": "bad id"})), ["id", "output", "inputs"])

    def test_round_trip_warning(self):
        rule = fcu_mode()
        rule["actions"][1]["set"] = [{"alias": "mode", "value": "Heat"}]
        self.assertEqual(composite_rule_issues(rule), [])
        self.assertEqual(fields(composite.round_trip_warnings(rule)), ["actions[1]"])


class CompositeRulesListTest(SimpleTestCase):
    def test_repeated_ids_and_outputs(self):
        _, general = composite_rules_issues([FCU_MODE, FCU_MODE])
        self.assertEqual(len(general), 2)

    def test_output_with_a_plain_rule(self):
        _, general = composite_rules_issues([FCU_MODE], {"fcumode"})
        self.assertIn("fcumode", general[0].message)

    def test_per_rule_issues(self):
        per_rule, general = composite_rules_issues([FCU_MODE, {"id": "x"}])
        self.assertEqual(per_rule[0], [])
        self.assertTrue(per_rule[1])
        self.assertEqual(general, [])

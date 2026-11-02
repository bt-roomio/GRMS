from django.test import SimpleTestCase

from services.mapping.engine import (
    SKIP,
    MappingError,
    ranges_to_external,
    to_external,
    to_grms,
)


def rule(transform, value_type="integer", **fields):
    return {"tag_name": "tag", "external": {"value_type": value_type}, "transform": transform, **fields}


def enum(*pairs):
    return {"type": "enum", "map": [{"grms": grms, "external": external} for grms, external in pairs]}


ON_OFF = rule(enum((False, 0), (True, 1)))
FAN_SPEED = rule(enum(("Low", 1), ("Medium", 2), ("High", 3)))
DIMMER = rule(
    {"type": "range", "grms": {"min": 0, "max": 100}, "external": {"min": 0, "max": 100, "step": 10}},
    on_invalid="clamp",
)
DIMMER_255 = rule(
    {"type": "range", "grms": {"min": 0, "max": 255, "step": 1}, "external": {"min": 0, "max": 100}},
    on_invalid="clamp",
)
SETPOINT = rule({"type": "passthrough"}, value_type="number", on_invalid="clamp")
TENTHS = rule({"type": "linear", "ops": [{"op": "multiply", "value": 0.1}]}, value_type="number")


class EnumTest(SimpleTestCase):
    def test_both_ways(self):
        self.assertEqual(to_external(FAN_SPEED, "Medium"), 2)
        self.assertEqual(to_grms(FAN_SPEED, 3), "High")

    def test_boolean_tag(self):
        self.assertEqual(to_external(ON_OFF, True), 1)
        self.assertIs(to_grms(ON_OFF, 0), False)

    def test_types_stay_apart(self):
        # 1 and True are equal in Python; the enum must not confuse them.
        both = rule(enum((True, "on"), (1, "one")), value_type="string")
        self.assertEqual(to_external(both, True), "on")
        self.assertEqual(to_external(both, 1), "one")

    def test_integral_float_matches_int(self):
        # A value stored in dbl_v comes back as 1.0.
        self.assertEqual(to_external(rule(enum((1, 10))), 1.0), 10)

    def test_query_string_value_is_parsed(self):
        self.assertEqual(to_grms(FAN_SPEED, "2"), "Medium")

    def test_unknown_value(self):
        with self.assertRaises(MappingError) as read:
            to_external(FAN_SPEED, "Turbo")
        self.assertEqual(read.exception.code, "unmapped")
        with self.assertRaises(MappingError) as write:
            to_grms(FAN_SPEED, 4)
        self.assertEqual(write.exception.code, "unmapped")

    def test_skip(self):
        self.assertIs(to_grms({**FAN_SPEED, "on_invalid": "skip"}, 4), SKIP)


class RangeTest(SimpleTestCase):
    def test_snaps_to_the_external_step(self):
        # The example from the spec: "55" -> 55 -> step 10 -> 60.
        self.assertEqual(to_grms(DIMMER, "55"), 60)
        self.assertEqual(to_grms(DIMMER, 54), 50)
        self.assertEqual(to_external(DIMMER, 47), 50)

    def test_scales(self):
        self.assertEqual(to_external(DIMMER_255, 255), 100)
        self.assertEqual(to_external(DIMMER_255, 128), 50)
        self.assertEqual(to_grms(DIMMER_255, 50), 128)  # 127.5 rounds half up on the grms step

    def test_invert(self):
        inverted = rule({**DIMMER_255["transform"], "invert": True})
        self.assertEqual(to_external(inverted, 0), 100)
        self.assertEqual(to_grms(inverted, 100), 0)

    def test_out_of_range_write(self):
        self.assertEqual(to_grms(DIMMER, 150), 100)
        with self.assertRaises(MappingError):
            to_grms({**DIMMER, "on_invalid": "reject"}, 150)

    def test_out_of_range_read_is_clamped(self):
        self.assertEqual(to_external(DIMMER, 120), 100)

    def test_wrong_type(self):
        with self.assertRaises(MappingError) as write:
            to_grms(DIMMER, "bright")
        self.assertEqual(write.exception.code, "type")
        with self.assertRaises(MappingError):
            to_grms(DIMMER, True)


class LinearTest(SimpleTestCase):
    def test_inverse_is_built(self):
        self.assertEqual(to_external(TENTHS, 225), 22.5)
        self.assertEqual(to_grms(TENTHS, 22.5), 225)

    def test_chain(self):
        fahrenheit = rule(
            {"type": "linear", "ops": [{"op": "multiply", "value": 1.8}, {"op": "add", "value": 32}]},
            value_type="number",
        )
        self.assertEqual(to_external(fahrenheit, 100), 212)
        self.assertEqual(to_grms(fahrenheit, 212), 100)

    def test_integer_external_rounds(self):
        self.assertEqual(to_external({**TENTHS, "external": {"value_type": "integer"}}, 225), 23)


class PassthroughTest(SimpleTestCase):
    def test_clamped_by_tag_ranges(self):
        # Hoteza allows 16-32, the tag only 16-30.
        self.assertEqual(to_grms(SETPOINT, 22, ["16-30"]), 22)
        self.assertEqual(to_grms(SETPOINT, 32, ["16-30"]), 30)
        self.assertEqual(to_grms(SETPOINT, 10, ["16-30"]), 16)

    def test_nearest_numeric_range(self):
        self.assertEqual(to_grms(SETPOINT, 26, ["16-20", "24-30"]), 26)
        self.assertEqual(to_grms(SETPOINT, 21, ["16-20", "24-30"]), 20)
        self.assertEqual(to_grms(SETPOINT, 23, ["16-20", "24-30"]), 24)

    def test_rejected_by_tag_ranges(self):
        with self.assertRaises(MappingError):
            to_grms({**SETPOINT, "on_invalid": "reject"}, 32, ["16-30"])
        with self.assertRaises(MappingError):
            to_grms(FAN_SPEED, 3, ["Low", "Medium"])  # this fan coil has no High

    def test_no_tag_ranges_means_no_check(self):
        self.assertEqual(to_grms(SETPOINT, 40), 40)

    def test_string(self):
        self.assertEqual(to_external(rule({"type": "passthrough"}, value_type="string"), "Eco"), "Eco")


class RangeBoundsTest(SimpleTestCase):
    """A range rule keeps incoming values within its external bounds, as on_invalid says."""

    def test_reject(self):
        with self.assertRaises(MappingError):
            to_grms({**DIMMER, "on_invalid": "reject"}, 150)

    def test_skip(self):
        self.assertIs(to_grms({**DIMMER, "on_invalid": "skip"}, 150), SKIP)

    def test_clamp(self):
        self.assertEqual(to_grms(DIMMER, 150), 100)

    def test_const(self):
        dimmer = {**DIMMER, "on_invalid": "const", "on_invalid_value": 0}
        self.assertEqual(to_grms(dimmer, 150), 0)
        self.assertEqual(to_grms(dimmer, 50), 50)  # a valid value is converted as usual


class ConstTest(SimpleTestCase):
    def test_unmapped_enum_value(self):
        fan_speed = {**FAN_SPEED, "on_invalid": "const", "on_invalid_value": "Low"}
        self.assertEqual(to_grms(fan_speed, 9), "Low")

    def test_value_outside_tag_ranges(self):
        setpoint = {**SETPOINT, "on_invalid": "const", "on_invalid_value": 22}
        self.assertEqual(to_grms(setpoint, 40, ["16-30"]), 22)

    def test_wrong_type_is_still_rejected(self):
        fan_speed = {**FAN_SPEED, "on_invalid": "const", "on_invalid_value": "Low"}
        with self.assertRaises(MappingError) as write:
            to_grms(fan_speed, "fast")
        self.assertEqual(write.exception.code, "type")


class DirectionTest(SimpleTestCase):
    def test_write_only_rule_leaves_reads_alone(self):
        scene = {**ON_OFF, "direction": "to_grms"}
        self.assertIs(to_external(scene, True), True)
        self.assertIs(to_grms(scene, 1), True)

    def test_read_only_rule_refuses_writes(self):
        with self.assertRaises(MappingError) as write:
            to_grms({**ON_OFF, "direction": "to_external"}, 1)
        self.assertEqual(write.exception.code, "direction")

    def test_number_stored_as_string_is_read(self):
        # A device may report a numeric value as a string (str_v).
        self.assertEqual(to_external(DIMMER, "47"), 50)
        with self.assertRaises(MappingError) as read:
            to_external(DIMMER, "bright")
        self.assertEqual(read.exception.code, "type")

    def test_missing_value_stays_missing(self):
        self.assertIsNone(to_external(FAN_SPEED, None))


class RangesToExternalTest(SimpleTestCase):
    def test_enum_drops_unmapped(self):
        self.assertEqual(ranges_to_external(FAN_SPEED, ["Low", "High", "Turbo"]), [1, 3])
        self.assertEqual(ranges_to_external(ON_OFF, [False, True]), [0, 1])

    def test_numeric_range_keeps_its_form(self):
        self.assertEqual(ranges_to_external(DIMMER_255, ["0-255"]), ["0-100"])
        self.assertEqual(ranges_to_external(TENTHS, ["160-300", 250]), ["16-30", 25])

    def test_integer_range_keeps_integer_bounds(self):
        # 0..127 of 255 is 0..49.8 of 100: an integer integrator may send 0..49.
        self.assertEqual(ranges_to_external(DIMMER_255, ["0-127"]), ["0-49"])
        self.assertEqual(
            ranges_to_external({**DIMMER_255, "external": {"value_type": "number"}}, ["0-127"]), ["0-49.803921569"]
        )
        # No integer lies within 0.39..0.78.
        self.assertEqual(ranges_to_external(DIMMER_255, ["1-2"]), [])

    def test_range_with_spaces(self):
        self.assertEqual(ranges_to_external(DIMMER_255, [" 0 - 255 "]), ["0-100"])

    def test_passthrough(self):
        self.assertEqual(ranges_to_external(SETPOINT, ["16-30"]), ["16-30"])

    def test_duplicates_collapse(self):
        self.assertEqual(ranges_to_external(DIMMER, [0, 1, 2]), [0])

    def test_none(self):
        self.assertIsNone(ranges_to_external(FAN_SPEED, None))


class RoundTripTest(SimpleTestCase):
    """Writing what a read returned must give back the same GRMS value."""

    def assert_round_trip(self, mapping_rule, grms_values):
        for value in grms_values:
            with self.subTest(value=value):
                self.assertEqual(to_grms(mapping_rule, to_external(mapping_rule, value)), value)

    def test_enum(self):
        self.assert_round_trip(FAN_SPEED, ["Low", "Medium", "High"])
        self.assert_round_trip(ON_OFF, [False, True])

    def test_range_on_the_grid(self):
        self.assert_round_trip(DIMMER, range(0, 101, 10))

    def test_range_scaled(self):
        self.assert_round_trip(DIMMER_255, [0, 51, 102, 153, 204, 255])

    def test_linear(self):
        self.assert_round_trip(TENTHS, [160, 225, 300])

    def test_passthrough(self):
        self.assert_round_trip(SETPOINT, [16, 22.5, 30])

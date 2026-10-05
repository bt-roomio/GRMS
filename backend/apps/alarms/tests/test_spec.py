from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from alarms.services.spec import eval_spec
from alarms.tests.factories import snapshot

SIMPLE = {"type": "SIMPLE"}
DURATION = {"type": "DURATION", "unit": "MINUTES", "predicate": {"defaultValue": 10}}
REPEATING = {"type": "REPEATING", "predicate": {"defaultValue": 3}}


class SimpleSpecTest(SimpleTestCase):
    def test_fires_on_the_first_match(self):
        fired, state = eval_spec(SIMPLE, None, True, timezone.now(), snapshot())
        self.assertTrue(fired)
        self.assertIsNone(state)

    def test_does_not_fire_without_a_match(self):
        fired, _ = eval_spec(SIMPLE, None, False, timezone.now(), snapshot())
        self.assertFalse(fired)


class DurationSpecTest(SimpleTestCase):
    def setUp(self):
        self.now = timezone.now()

    def test_first_tick_only_starts_the_clock(self):
        fired, state = eval_spec(DURATION, None, True, self.now, snapshot())
        self.assertFalse(fired)
        self.assertIn("since", state or {})

    def test_fires_once_the_interval_has_passed(self):
        _, state = eval_spec(DURATION, None, True, self.now, snapshot())

        fired, _ = eval_spec(DURATION, state, True, self.now + timedelta(minutes=9), snapshot())
        self.assertFalse(fired)

        fired, _ = eval_spec(DURATION, state, True, self.now + timedelta(minutes=10), snapshot())
        self.assertTrue(fired)

    def test_a_broken_streak_resets_the_clock(self):
        _, state = eval_spec(DURATION, None, True, self.now, snapshot())

        fired, state = eval_spec(DURATION, state, False, self.now + timedelta(minutes=5), snapshot())
        self.assertFalse(fired)
        self.assertIsNone(state)

        # The condition has to hold *continuously*, so the clock starts over.
        fired, state = eval_spec(DURATION, state, True, self.now + timedelta(minutes=6), snapshot())
        self.assertFalse(fired)
        fired, _ = eval_spec(DURATION, state, True, self.now + timedelta(minutes=15), snapshot())
        self.assertFalse(fired)

    def test_duration_can_come_from_an_attribute(self):
        spec = {
            "type": "DURATION",
            "unit": "MINUTES",
            "predicate": {
                "defaultValue": 10,
                "dynamicValue": {"sourceType": "CURRENT_ROOM", "sourceAttribute": "offlineDelay"},
            },
        }
        data = snapshot(room_attrs={"offlineDelay": 2})

        _, state = eval_spec(spec, None, True, self.now, data)
        fired, _ = eval_spec(spec, state, True, self.now + timedelta(minutes=2), data)
        self.assertTrue(fired)

    def test_units(self):
        spec = {"type": "DURATION", "unit": "SECONDS", "predicate": {"defaultValue": 30}}
        _, state = eval_spec(spec, None, True, self.now, snapshot())
        fired, _ = eval_spec(spec, state, True, self.now + timedelta(seconds=30), snapshot())
        self.assertTrue(fired)


class RepeatingSpecTest(SimpleTestCase):
    def setUp(self):
        self.now = timezone.now()

    def test_fires_on_the_nth_consecutive_match(self):
        state = None
        for expected in (False, False, True):
            fired, state = eval_spec(REPEATING, state, True, self.now, snapshot())
            self.assertEqual(fired, expected)

    def test_a_miss_resets_the_counter(self):
        _, state = eval_spec(REPEATING, None, True, self.now, snapshot())
        _, state = eval_spec(REPEATING, state, True, self.now, snapshot())

        fired, state = eval_spec(REPEATING, state, False, self.now, snapshot())
        self.assertFalse(fired)
        self.assertIsNone(state)

        fired, _ = eval_spec(REPEATING, state, True, self.now, snapshot())
        self.assertFalse(fired)

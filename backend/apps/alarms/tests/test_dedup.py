from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from alarms.models import Alarm
from alarms.services.engine import evaluate
from alarms.tests.base import DEVICE_ID, TENANT_ID, AlarmTestCase, offline_rule


class DeduplicationTest(AlarmTestCase):
    def setUp(self):
        self.now = timezone.now()
        self.set_rules(offline_rule(minutes=0))
        self.set_attribute("active", False)

    def test_repeated_passes_keep_a_single_active_alarm(self):
        for minute in range(5):
            evaluate(now=self.now + timedelta(minutes=minute))

        self.assertEqual(Alarm.objects.filter(originator_id=DEVICE_ID, cleared=False).count(), 1)

    def test_a_second_detector_cannot_insert_a_duplicate(self):
        # The MQTT disconnect topic and the watchdog notice the same outage up
        # to a minute apart; the partial unique index is what makes that safe.
        evaluate(now=self.now)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Alarm.objects.create(
                tenant_id=TENANT_ID,
                originator_id=DEVICE_ID,
                alarm_type="Device Offline",
                severity="MAJOR",
            )

    def test_cleared_alarms_do_not_block_a_new_one(self):
        evaluate(now=self.now)
        Alarm.objects.filter(originator_id=DEVICE_ID).update(cleared=True, clear_ts=self.now)

        Alarm.objects.create(
            tenant_id=TENANT_ID,
            originator_id=DEVICE_ID,
            alarm_type="Device Offline",
            severity="MAJOR",
        )
        self.assertEqual(Alarm.objects.filter(originator_id=DEVICE_ID).count(), 2)

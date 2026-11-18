from datetime import timedelta

from django.utils import timezone

from alarms.models import Alarm
from alarms.services.engine import evaluate
from alarms.templates import device_offline_rule, gateway_offline_rule
from alarms.tests.base import (
    DEVICE_ID,
    OTHER_DEVICE_ID,
    ROOM_ID,
    TENANT_ID,
    AlarmTestCase,
    offline_rule,
    temperature_rule,
)
from main.models import Device
from shuttle.models import Relation


class PropagationTest(AlarmTestCase):
    def setUp(self):
        self.now = timezone.now()
        Relation.objects.create(
            from_id_id=OTHER_DEVICE_ID,
            from_type="DEVICE",
            to_id_id=DEVICE_ID,
            to_type="DEVICE",
            relation_type_group="COMMON",
            relation_type="Contains",
        )

    def test_related_devices_land_in_propagate_entity_ids(self):
        self.set_rules(offline_rule(minutes=0, propagate=True))
        self.set_attribute("active", False, device_id=OTHER_DEVICE_ID)

        evaluate(now=self.now)

        alarm = Alarm.objects.get(originator_id=OTHER_DEVICE_ID)
        self.assertEqual([str(entity_id) for entity_id in alarm.propagate_entity_ids], [DEVICE_ID])
        # And that is what makes the alarm visible from the device behind it.
        self.assertTrue(Alarm.objects.for_device(DEVICE_ID).filter(id=alarm.id).exists())

    def test_relation_types_narrow_the_targets(self):
        rule = offline_rule(minutes=0, propagate=True, propagateRelationTypes=["Manages"])
        self.set_rules(rule)
        self.set_attribute("active", False, device_id=OTHER_DEVICE_ID)

        evaluate(now=self.now)

        self.assertEqual(Alarm.objects.get(originator_id=OTHER_DEVICE_ID).propagate_entity_ids, [])

    def test_propagate_to_owner_and_tenant(self):
        rule = offline_rule(minutes=0, propagateToOwner=True, propagateToTenant=True)
        self.set_rules(rule)
        self.set_attribute("active", False)

        evaluate(now=self.now)

        targets = {str(entity_id) for entity_id in Alarm.objects.get(originator_id=DEVICE_ID).propagate_entity_ids}
        self.assertEqual(targets, {ROOM_ID, TENANT_ID})


class GatewayCascadeTest(AlarmTestCase):
    """
    The whole point of the ``gatewayActive`` filter: a dead gateway is one
    incident, not one per device behind it.
    """

    def setUp(self):
        self.now = timezone.now()
        self.set_rules(device_offline_rule(), gateway_offline_rule())

        Device.objects.filter(pk=OTHER_DEVICE_ID).update(additional_info={"gateway": True})
        Relation.objects.create(
            from_id_id=OTHER_DEVICE_ID,
            from_type="DEVICE",
            to_id_id=DEVICE_ID,
            to_type="DEVICE",
            relation_type_group="COMMON",
            relation_type="Contains",
        )

        # The gateway is down and has taken its device with it, exactly as the
        # watchdog leaves things.
        self.set_attribute("active", False, device_id=OTHER_DEVICE_ID)
        self.set_attribute("active", False, device_id=DEVICE_ID)
        self.set_attribute("notifyOnOffline", True, device_id=DEVICE_ID)
        self.set_attribute("gatewayActive", False, device_id=DEVICE_ID)

    def run_until_fired(self):
        evaluate(now=self.now)
        evaluate(now=self.now + timedelta(minutes=11))

    def test_only_the_gateway_raises_an_alarm(self):
        self.run_until_fired()

        self.assertEqual(Alarm.objects.count(), 1)
        alarm = Alarm.objects.get()
        self.assertEqual(alarm.alarm_type, "Gateway Offline")
        self.assertEqual(alarm.severity, "CRITICAL")
        self.assertEqual(str(alarm.originator_id), OTHER_DEVICE_ID)

    def test_the_gateway_alarm_is_visible_from_its_devices(self):
        self.run_until_fired()
        self.assertEqual(Alarm.objects.for_device(DEVICE_ID).count(), 1)

    def test_a_device_down_on_its_own_still_raises(self):
        self.set_attribute("active", True, device_id=OTHER_DEVICE_ID)
        self.set_attribute("gatewayActive", True, device_id=DEVICE_ID)

        self.run_until_fired()

        alarm = Alarm.objects.get()
        self.assertEqual(alarm.alarm_type, "Device Offline")
        self.assertEqual(str(alarm.originator_id), DEVICE_ID)

    def test_the_toggle_silences_a_device(self):
        self.set_attribute("active", True, device_id=OTHER_DEVICE_ID)
        self.set_attribute("gatewayActive", True, device_id=DEVICE_ID)
        self.set_attribute("notifyOnOffline", False, device_id=DEVICE_ID)

        self.run_until_fired()

        self.assertFalse(Alarm.objects.exists())


class DeadGatewaySuppressionTest(AlarmTestCase):
    """
    Behind a dead gateway no rule raises an alarm, even one that does not
    mention ``gatewayActive`` — the guard lives in the evaluator.
    """

    def setUp(self):
        self.now = timezone.now()
        Device.objects.filter(pk=OTHER_DEVICE_ID).update(additional_info={"gateway": True})

    def test_a_rule_without_the_guard_is_suppressed(self):
        self.set_rules(temperature_rule(threshold=30, attribute=None))
        self.set_telemetry("Room Temperature", 35.0)
        self.set_attribute("gatewayActive", False)

        evaluate(now=self.now)

        self.assertFalse(Alarm.objects.exists())

    def test_a_live_gateway_lets_the_rule_fire(self):
        self.set_rules(temperature_rule(threshold=30, attribute=None))
        self.set_telemetry("Room Temperature", 35.0)
        self.set_attribute("gatewayActive", True)

        evaluate(now=self.now)

        self.assertEqual(Alarm.objects.get().alarm_type, "High Temperature")

    def test_a_device_without_the_attribute_is_not_suppressed(self):
        self.set_rules(temperature_rule(threshold=30, attribute=None))
        self.set_telemetry("Room Temperature", 35.0)

        evaluate(now=self.now)

        self.assertTrue(Alarm.objects.exists())

    def test_the_gateway_itself_is_never_suppressed(self):
        self.set_rules(offline_rule(minutes=0))
        self.set_attribute("active", False, device_id=OTHER_DEVICE_ID)
        self.set_attribute("gatewayActive", False, device_id=OTHER_DEVICE_ID)

        evaluate(now=self.now)

        self.assertEqual(str(Alarm.objects.get().originator_id), OTHER_DEVICE_ID)

    def test_the_duration_restarts_after_the_gateway_recovers(self):
        self.set_rules(offline_rule(minutes=10))
        self.set_attribute("active", False)
        self.set_attribute("gatewayActive", True)
        evaluate(now=self.now)

        self.set_attribute("gatewayActive", False)
        evaluate(now=self.now + timedelta(minutes=3))

        # Back after 6 minutes: without the reset the streak started at 0
        # would be 11 minutes old here and fire on data frozen half that time.
        self.set_attribute("gatewayActive", True)
        evaluate(now=self.now + timedelta(minutes=6))
        evaluate(now=self.now + timedelta(minutes=11))
        self.assertFalse(Alarm.objects.exists())

        evaluate(now=self.now + timedelta(minutes=16))
        self.assertTrue(Alarm.objects.exists())

    def test_the_clear_rule_still_runs(self):
        self.set_rules(offline_rule(minutes=0))
        self.set_attribute("active", False)
        evaluate(now=self.now)

        self.set_attribute("gatewayActive", False)
        self.set_attribute("active", True)
        evaluate(now=self.now + timedelta(minutes=1))

        self.assertTrue(Alarm.objects.get().cleared)

from django.core.management import call_command

from alarms.services.attributes import get_server_attribute
from alarms.tests.base import DEVICE_ID, FOREIGN_DEVICE_ID, OTHER_DEVICE_ID, AlarmTestCase
from core.utils.get_time import get_mil_sec
from main.models import Device
from shuttle.models import AttributeKv, Relation

GATEWAY_ID = OTHER_DEVICE_ID
SECOND_GATEWAY_ID = FOREIGN_DEVICE_ID


class GatewayWatchdogTest(AlarmTestCase):
    """
    The watchdog keeps ``gatewayActive`` in step with the gateway's state on
    every tick, whoever flipped the gateway's ``active``.
    """

    def setUp(self):
        self.now = get_mil_sec()
        Device.objects.filter(pk__in=[GATEWAY_ID, SECOND_GATEWAY_ID]).update(additional_info={"gateway": True})
        self.relate(GATEWAY_ID, DEVICE_ID)

    def relate(self, gateway_id, device_id):
        Relation.objects.create(
            from_id_id=gateway_id,
            from_type="DEVICE",
            to_id_id=device_id,
            to_type="DEVICE",
            relation_type_group="COMMON",
            relation_type="Contains",
        )

    def gateway_state(self, *, active, active_age_sec, activity_age_sec, gateway_id=GATEWAY_ID):
        """Write the two attributes the way mq-async leaves them, aged as given."""
        activity_ts = self.now - activity_age_sec * 1000
        values = {
            "active": {"bool_v": active, "last_update_ts": self.now - active_age_sec * 1000},
            "lastActivityTime": {"long_v": activity_ts, "last_update_ts": activity_ts},
        }
        for key, fields in values.items():
            scope = {"entity_id": gateway_id, "attribute_type": AttributeKv.SERVER_SCOPE, "attribute_key": key}
            AttributeKv.objects.get_or_create(**scope, defaults={"entity_type": "DEVICE"})
            # A queryset update: AttributeKv.save() would stamp last_update_ts
            # with the current time.
            AttributeKv.objects.filter(**scope).update(**fields)

    def tick(self):
        call_command("active_attribute_server_scope")

    def gateway_active(self, device_id=DEVICE_ID):
        return get_server_attribute(device_id, "gatewayActive")

    def test_a_gateway_marked_down_by_mq_async_reaches_its_devices(self):
        # The production case: a disconnect topic set active=false, so the
        # timeout pass never sees the gateway, and its devices still say true.
        self.gateway_state(active=False, active_age_sec=120, activity_age_sec=120)
        self.set_attribute("gatewayActive", True)

        self.tick()

        self.assertIs(self.gateway_active(), False)

    def test_a_short_disconnect_does_not_suppress_the_devices(self):
        self.gateway_state(active=False, active_age_sec=10, activity_age_sec=10)
        self.set_attribute("gatewayActive", True)

        self.tick()

        self.assertIs(self.gateway_active(), True)

    def test_a_disconnect_held_past_the_hold_counts_even_with_fresh_activity(self):
        # Repeated disconnect messages keep lastActivityTime fresh while active
        # stays false.
        self.gateway_state(active=False, active_age_sec=120, activity_age_sec=5)

        self.tick()

        self.assertIs(self.gateway_active(), False)

    def test_a_silent_gateway_is_deactivated_and_its_devices_follow_in_the_same_tick(self):
        self.gateway_state(active=True, active_age_sec=300, activity_age_sec=300)
        self.set_attribute("active", True)

        self.tick()

        self.assertIs(get_server_attribute(GATEWAY_ID, "active"), False)
        self.assertIs(get_server_attribute(DEVICE_ID, "active"), False)
        self.assertIs(self.gateway_active(), False)

    def test_a_recovered_gateway_lifts_the_suppression(self):
        self.gateway_state(active=True, active_age_sec=5, activity_age_sec=5)
        self.set_attribute("gatewayActive", False)

        self.tick()

        self.assertIs(self.gateway_active(), True)

    def test_a_relation_added_after_the_outage_is_picked_up(self):
        self.gateway_state(active=False, active_age_sec=120, activity_age_sec=120)
        self.tick()

        Relation.objects.filter(to_id_id=DEVICE_ID).delete()
        self.relate(GATEWAY_ID, SECOND_GATEWAY_ID)
        self.tick()

        self.assertIs(self.gateway_active(SECOND_GATEWAY_ID), False)

    def test_a_device_behind_a_live_and_a_dead_gateway_stays_active(self):
        self.gateway_state(active=False, active_age_sec=120, activity_age_sec=120)
        self.gateway_state(active=True, active_age_sec=5, activity_age_sec=5, gateway_id=SECOND_GATEWAY_ID)
        self.relate(SECOND_GATEWAY_ID, DEVICE_ID)

        self.tick()
        written_at = AttributeKv.objects.get(entity_id=DEVICE_ID, attribute_key="gatewayActive").last_update_ts
        self.tick()

        row = AttributeKv.objects.get(entity_id=DEVICE_ID, attribute_key="gatewayActive")
        self.assertIs(row.bool_v, True)
        self.assertEqual(row.last_update_ts, written_at)

    def test_a_gateway_that_never_reported_leaves_its_devices_alone(self):
        self.tick()

        self.assertIsNone(self.gateway_active())

from datetime import timedelta

from django.core.cache import caches
from django.urls import reverse
from django.utils import timezone

from alarms.models import Alarm, AlarmComment
from alarms.tests.base import (
    DEVICE_ID,
    FOREIGN_DEVICE_ID,
    OTHER_TENANT_ID,
    PROFILE_ID,
    ROOM_ID,
    TENANT_ID,
    offline_rule,
    temperature_rule,
)
from core.tests.base import BaseTestCase


class AlarmAPITestCase(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "customer.yaml",
        "room.yaml",
        "device_profile.yaml",
        "device.yaml",
        "roles_permissions.yaml",
        "users.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.now = timezone.now()

    def make_alarm(self, tenant_id=TENANT_ID, originator_id=DEVICE_ID, **overrides):
        defaults = {
            "alarm_type": "Device Offline",
            "severity": "MAJOR",
            "start_ts": self.now,
            "end_ts": self.now,
            "room_id": ROOM_ID if originator_id == DEVICE_ID else None,
            "details": {"message": "Device Offline on DHT11"},
        }
        return Alarm.objects.create(tenant_id=tenant_id, originator_id=originator_id, **{**defaults, **overrides})


class AlarmListTest(AlarmAPITestCase):
    def test_list_returns_the_tenant_journal(self):
        self.make_alarm()

        response = self.get(reverse("alarms:alarm-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        row = response.data["results"][0]
        self.assertEqual(row["alarm_type"], "Device Offline")
        self.assertEqual(row["status"], "ACTIVE_UNACK")
        self.assertEqual(row["originator_name"], "DHT11 Demo Device")
        self.assertEqual(row["room_number"], "101")

    def test_another_tenants_alarms_are_invisible(self):
        self.make_alarm(tenant_id=OTHER_TENANT_ID, originator_id=FOREIGN_DEVICE_ID)

        response = self.get(reverse("alarms:alarm-list"))
        self.assertEqual(response.data["count"], 0)

    def test_status_filter(self):
        self.make_alarm()
        self.make_alarm(alarm_type="High Temperature", cleared=True, clear_ts=self.now)

        active = self.get(reverse("alarms:alarm-list"), {"status": "ACTIVE"})
        self.assertEqual(active.data["count"], 1)
        self.assertEqual(active.data["results"][0]["alarm_type"], "Device Offline")

        cleared = self.get(reverse("alarms:alarm-list"), {"status": "CLEARED"})
        self.assertEqual(cleared.data["count"], 1)

    def test_type_severity_and_device_filters(self):
        self.make_alarm()
        self.make_alarm(
            alarm_type="High Temperature", severity="CRITICAL", originator_id="a1561fb2-e031-42ce-812a-0ce84843c0f0"
        )

        by_type = self.get(reverse("alarms:alarm-list"), {"alarm_type": ["High Temperature"]})
        self.assertEqual(by_type.data["count"], 1)

        by_severity = self.get(reverse("alarms:alarm-list"), {"severity": ["CRITICAL"]})
        self.assertEqual(by_severity.data["count"], 1)

        by_device = self.get(reverse("alarms:alarm-list"), {"device": DEVICE_ID})
        self.assertEqual(by_device.data["count"], 1)
        self.assertEqual(by_device.data["results"][0]["alarm_type"], "Device Offline")

    def test_date_range_filter(self):
        self.make_alarm(start_ts=self.now - timedelta(days=3))

        inside = self.get(reverse("alarms:alarm-list"), {"date_from": (self.now - timedelta(days=5)).isoformat()})
        self.assertEqual(inside.data["count"], 1)

        outside = self.get(reverse("alarms:alarm-list"), {"date_from": (self.now - timedelta(days=1)).isoformat()})
        self.assertEqual(outside.data["count"], 0)

    def test_propagated_alarms_show_up_on_the_related_device(self):
        self.make_alarm(
            originator_id="a1561fb2-e031-42ce-812a-0ce84843c0f0",
            alarm_type="Gateway Offline",
            propagate=True,
            propagate_entity_ids=[DEVICE_ID],
        )

        response = self.get(reverse("alarms:alarm-list"), {"device": DEVICE_ID})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["alarm_type"], "Gateway Offline")

    def test_authentication_is_required(self):
        self.client.credentials()
        self.assertEqual(self.get(reverse("alarms:alarm-list")).status_code, 401)


class AlarmActionTest(AlarmAPITestCase):
    def setUp(self):
        super().setUp()
        self.alarm = self.make_alarm()

    def test_ack(self):
        response = self.post(reverse("alarms:alarm-ack", args=[self.alarm.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["acknowledged"])
        self.assertEqual(response.data["status"], "ACTIVE_ACK")

        self.alarm.refresh_from_db()
        self.assertIsNotNone(self.alarm.ack_ts)
        self.assertTrue(AlarmComment.objects.filter(alarm=self.alarm, comment__subtype="ACKNOWLEDGED").exists())

    def test_ack_is_idempotent(self):
        self.post(reverse("alarms:alarm-ack", args=[self.alarm.id]))
        first_ack = Alarm.objects.get(pk=self.alarm.id).ack_ts

        self.post(reverse("alarms:alarm-ack", args=[self.alarm.id]))
        self.assertEqual(Alarm.objects.get(pk=self.alarm.id).ack_ts, first_ack)
        self.assertEqual(AlarmComment.objects.filter(comment__subtype="ACKNOWLEDGED").count(), 1)

    def test_clear(self):
        response = self.post(reverse("alarms:alarm-clear", args=[self.alarm.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["cleared"])
        self.alarm.refresh_from_db()
        self.assertIsNotNone(self.alarm.clear_ts)

    def test_assign_and_unassign(self):
        user = self.karina()

        response = self.post(
            reverse("alarms:alarm-assign", args=[self.alarm.id]),
            data={"assignee": str(user.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["assignee"]["id"], str(user.id))

        response = self.post(
            reverse("alarms:alarm-assign", args=[self.alarm.id]),
            data={"assignee": None},
            format="json",
        )
        self.assertIsNone(response.data["assignee"])
        self.assertIsNone(Alarm.objects.get(pk=self.alarm.id).assign_ts)

    def karina(self):
        from users.models import User

        return User.objects.get(email="karina@gmail.com")

    def test_comments(self):
        response = self.post(
            reverse("alarms:alarm-comments", args=[self.alarm.id]),
            data={"text": "Выехал техник"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["comment"]["text"], "Выехал техник")

        listing = self.get(reverse("alarms:alarm-comments", args=[self.alarm.id]))
        self.assertEqual(len(listing.data), 1)

    def test_filter_by_assignee(self):
        user = self.karina()
        self.post(
            reverse("alarms:alarm-assign", args=[self.alarm.id]),
            data={"assignee": str(user.id)},
            format="json",
        )
        unassigned = self.make_alarm(alarm_type="High Temperature")

        mine = self.get(reverse("alarms:alarm-list"), {"assignee": str(user.id)})
        self.assertEqual(mine.data["count"], 1)
        self.assertEqual(mine.data["results"][0]["id"], str(self.alarm.id))

        nobody = self.get(reverse("alarms:alarm-list"), {"assignee": "none"})
        self.assertEqual(nobody.data["count"], 1)
        self.assertEqual(nobody.data["results"][0]["id"], str(unassigned.id))

    def test_delete_removes_the_alarm_and_its_comments(self):
        self.post(
            reverse("alarms:alarm-comments", args=[self.alarm.id]),
            data={"text": "Ложное срабатывание"},
            format="json",
        )

        response = self.delete(reverse("alarms:alarm-detail", args=[self.alarm.id]))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Alarm.objects.filter(pk=self.alarm.id).exists())
        self.assertFalse(AlarmComment.objects.filter(alarm_id=self.alarm.id).exists())

    def test_own_comment_can_be_edited_and_deleted(self):
        created = self.post(
            reverse("alarms:alarm-comments", args=[self.alarm.id]),
            data={"text": "Выехал техник"},
            format="json",
        )
        comment_id = created.data["id"]
        url = reverse("alarms:alarm-comment-detail", args=[self.alarm.id, comment_id])

        edited = self.put(url, data={"text": "Техник на месте"}, format="json")
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.data["comment"]["text"], "Техник на месте")
        self.assertTrue(edited.data["comment"]["edited"])

        self.assertEqual(self.delete(url).status_code, 204)
        self.assertFalse(AlarmComment.objects.filter(pk=comment_id).exists())

    def test_a_system_comment_is_read_only(self):
        self.post(reverse("alarms:alarm-ack", args=[self.alarm.id]))
        system = AlarmComment.objects.get(alarm=self.alarm, comment__subtype="ACKNOWLEDGED")
        url = reverse("alarms:alarm-comment-detail", args=[self.alarm.id, system.id])

        self.assertEqual(self.put(url, data={"text": "переписал"}, format="json").status_code, 403)
        self.assertEqual(self.delete(url).status_code, 403)
        self.assertTrue(AlarmComment.objects.filter(pk=system.id).exists())

    def test_a_foreign_alarm_is_a_404(self):
        foreign = self.make_alarm(tenant_id=OTHER_TENANT_ID, originator_id=FOREIGN_DEVICE_ID)
        self.assertEqual(self.get(reverse("alarms:alarm-detail", args=[foreign.id])).status_code, 404)


class AlarmBulkTest(AlarmAPITestCase):
    def test_bulk_ack_counts_only_what_it_changed(self):
        first = self.make_alarm()
        second = self.make_alarm(alarm_type="High Temperature")
        already = self.make_alarm(alarm_type="Low Temperature", acknowledged=True, ack_ts=self.now)

        response = self.post(
            reverse("alarms:alarm-bulk-ack"),
            data={"ids": [str(first.id), str(second.id), str(already.id)]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"updated": 2, "requested": 3})
        self.assertEqual(Alarm.objects.filter(acknowledged=True).count(), 3)

    def test_bulk_clear(self):
        first = self.make_alarm()
        second = self.make_alarm(alarm_type="High Temperature")

        response = self.post(
            reverse("alarms:alarm-bulk-clear"),
            data={"ids": [str(first.id), str(second.id)]},
            format="json",
        )

        self.assertEqual(response.data["updated"], 2)
        self.assertEqual(Alarm.objects.filter(cleared=True).count(), 2)
        self.assertEqual(AlarmComment.objects.filter(comment__subtype="CLEARED").count(), 2)

    def test_bulk_never_reaches_another_tenant(self):
        foreign = self.make_alarm(tenant_id=OTHER_TENANT_ID, originator_id=FOREIGN_DEVICE_ID)

        response = self.post(
            reverse("alarms:alarm-bulk-ack"),
            data={"ids": [str(foreign.id)]},
            format="json",
        )

        self.assertEqual(response.data["updated"], 0)
        foreign.refresh_from_db()
        self.assertFalse(foreign.acknowledged)


class AlarmSummaryTest(AlarmAPITestCase):
    def test_counters(self):
        self.make_alarm()
        self.make_alarm(alarm_type="High Temperature", severity="CRITICAL", acknowledged=True, ack_ts=self.now)
        self.make_alarm(alarm_type="Low Temperature", cleared=True, clear_ts=self.now)

        response = self.get(reverse("alarms:alarm-summary"))

        self.assertEqual(response.data["total"], 3)
        self.assertEqual(response.data["active"], 2)
        self.assertEqual(response.data["unacknowledged"], 1)
        self.assertEqual(response.data["by_severity"]["MAJOR"], 2)
        self.assertEqual(response.data["by_type"]["Device Offline"], 1)

    def test_types_endpoint(self):
        self.make_alarm()
        self.make_alarm(alarm_type="High Temperature")

        response = self.get(reverse("alarms:alarm-types"))
        self.assertEqual(response.data["results"], ["Device Offline", "High Temperature"])


class AvailableKeysTest(AlarmAPITestCase):
    fixtures = (*AlarmAPITestCase.fixtures, "ts_dictionary.yaml", "ts_kv_latest.yaml", "attribute_kv.yaml")

    def setUp(self):
        super().setUp()
        caches["default"].delete(f"alarms:available-keys:{TENANT_ID}")

    def test_only_keys_this_tenant_reports_are_offered(self):
        response = self.get(reverse("alarms:alarm-available-keys"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("humidity", response.data["timeseries"])
        # cpuUsage belongs to a device of another tenant.
        self.assertNotIn("cpuUsage", response.data["timeseries"])
        self.assertIn("is_gateway", response.data["entity_fields"])

    def test_search_narrows_the_list(self):
        response = self.get(reverse("alarms:alarm-available-keys"), {"search_value": "humid"})
        self.assertEqual(response.data["timeseries"], ["humidity"])


class PreviewTest(AlarmAPITestCase):
    fixtures = (*AlarmAPITestCase.fixtures, "ts_dictionary.yaml", "ts_kv_latest.yaml")

    def url(self):
        return reverse("alarms:rule-preview")

    def test_preview_counts_matching_devices_without_writing_anything(self):
        rule = temperature_rule(threshold=0, attribute=None)
        rule["createRules"]["MINOR"]["condition"]["condition"][0]["key"]["key"] = "humidity"

        response = self.post(self.url(), data={"device_profile": PROFILE_ID, "alarms": [rule]}, format="json")

        self.assertEqual(response.status_code, 200)
        alarm = response.data["alarms"][0]
        self.assertEqual(alarm["alarmType"], "High Temperature")
        self.assertEqual(alarm["create_rules"][0]["matched_count"], 1)
        self.assertFalse(Alarm.objects.exists())

    def test_a_malformed_rule_is_rejected_before_it_is_ever_stored(self):
        broken = offline_rule(minutes=0)
        broken["createRules"]["MAJOR"]["condition"]["condition"][0]["valueType"] = "NUMERIC"

        response = self.post(self.url(), data={"device_profile": PROFILE_ID, "alarms": [broken]}, format="json")
        self.assertEqual(response.status_code, 400)

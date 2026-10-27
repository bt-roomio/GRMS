from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from alarms.models import Alarm, AlarmRule
from alarms.services.engine import evaluate
from alarms.templates import catalogue, device_offline_rule, gateway_offline_rule
from alarms.tests.base import (
    OTHER_TENANT_ID,
    PROFILE_ID,
    TENANT_ID,
    AlarmTestCase,
    offline_rule,
    temperature_rule,
)
from core.tests.base import BaseTestCase
from main.models import DeviceProfile

# A second profile of the same tenant, from apps/main/fixtures.
PROFILE_TWO = "be17d30b-9785-4415-bfa5-e7fdaf19e57c"


def row(rule: dict, profile_id=PROFILE_ID, tenant_id=TENANT_ID, **extra) -> AlarmRule:
    return AlarmRule.objects.create(
        tenant_id=tenant_id,
        device_profile_id=profile_id,
        alarm_type=rule["alarmType"],
        create_rules=rule.get("createRules") or {},
        clear_rule=rule.get("clearRule"),
        propagate=bool(rule.get("propagate")),
        propagate_relation_types=rule.get("propagateRelationTypes") or [],
        **extra,
    )


class AlarmRuleAPITestCase(BaseTestCase):
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

    def body(self, rule=None, profile_id=PROFILE_ID, **extra) -> dict:
        """The CRUD body: the TB rule object plus the GRMS envelope."""
        return {"device_profile": profile_id, **(rule or device_offline_rule()), **extra}

    def list_url(self):
        return reverse("alarms:rule-list")

    def detail_url(self, pk):
        return reverse("alarms:rule-detail", args=[pk])


class AlarmRuleCrudTest(AlarmRuleAPITestCase):
    def test_create_stores_the_rule_and_fills_in_format_defaults(self):
        rule = device_offline_rule()
        del rule["createRules"]["MAJOR"]["condition"]["spec"]

        response = self.post(self.list_url(), data=self.body(rule), format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["alarmType"], "Device Offline")
        self.assertTrue(response.data["enabled"])
        # The TB validator normalises on the way in.
        self.assertEqual(response.data["createRules"]["MAJOR"]["condition"]["spec"], {"type": "SIMPLE"})
        self.assertEqual(response.data["propagateRelationTypes"], [])

        stored = AlarmRule.objects.get(pk=response.data["id"])
        # The tenant follows the profile, it is never read from the body.
        self.assertEqual(str(stored.tenant_id), TENANT_ID)
        self.assertEqual(stored.created_by.email, "karina@gmail.com")

    def test_a_malformed_tree_is_rejected(self):
        broken = device_offline_rule()
        broken["createRules"]["MAJOR"]["condition"]["condition"][0]["valueType"] = "NUMERIC"

        response = self.post(self.list_url(), data=self.body(broken), format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("createRules", response.data)
        self.assertFalse(AlarmRule.objects.exists())

    def test_duplicate_type_on_one_profile_is_rejected(self):
        self.post(self.list_url(), data=self.body(), format="json")

        response = self.post(self.list_url(), data=self.body(), format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("alarmType", response.data)
        self.assertEqual(AlarmRule.objects.count(), 1)

    def test_the_same_type_on_another_profile_is_allowed(self):
        self.post(self.list_url(), data=self.body(), format="json")

        response = self.post(self.list_url(), data=self.body(profile_id=PROFILE_TWO), format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(AlarmRule.objects.filter(alarm_type="Device Offline").count(), 2)

    def test_enabled_toggles_without_resending_the_tree(self):
        rule = row(device_offline_rule())

        response = self.put(self.detail_url(rule.id), data={"enabled": False}, format="json")

        self.assertEqual(response.status_code, 200)
        rule.refresh_from_db()
        self.assertFalse(rule.enabled)
        self.assertEqual(rule.create_rules, device_offline_rule()["createRules"])
        self.assertEqual(rule.updated_by.email, "karina@gmail.com")

    def test_update_validates_the_new_tree(self):
        rule = row(device_offline_rule())
        broken = device_offline_rule()["createRules"]
        broken["MAJOR"]["condition"]["spec"] = {"type": "DURATION", "unit": "MINUTES", "predicate": {"defaultValue": 0}}

        response = self.put(self.detail_url(rule.id), data={"createRules": broken}, format="json")

        self.assertEqual(response.status_code, 400)

    def test_delete_removes_the_row(self):
        rule = row(device_offline_rule())

        response = self.delete(self.detail_url(rule.id))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(AlarmRule.objects.exists())

    def test_list_filters_by_profile_and_by_enabled(self):
        row(device_offline_rule())
        row(gateway_offline_rule(), enabled=False)
        row(temperature_rule(), profile_id=PROFILE_TWO)

        everything = self.get(self.list_url())
        self.assertEqual(everything.data["count"], 3)

        by_profile = self.get(self.list_url(), {"device_profile": PROFILE_ID})
        self.assertEqual(by_profile.data["count"], 2)

        disabled = self.get(self.list_url(), {"enabled": False})
        self.assertEqual(disabled.data["count"], 1)
        self.assertEqual(disabled.data["results"][0]["alarmType"], "Gateway Offline")

    def test_another_tenants_rules_are_invisible(self):
        foreign_profile = DeviceProfile.objects.create(name="foreign", type="DEFAULT", tenant_id=OTHER_TENANT_ID)
        foreign = row(device_offline_rule(), profile_id=foreign_profile.id, tenant_id=OTHER_TENANT_ID)

        listed = self.get(self.list_url())
        self.assertEqual(listed.data["count"], 0)
        self.assertEqual(self.get(self.detail_url(foreign.id)).status_code, 404)

    def test_a_foreign_profile_cannot_be_targeted(self):
        foreign_profile = DeviceProfile.objects.create(name="foreign", type="DEFAULT", tenant_id=OTHER_TENANT_ID)

        response = self.post(self.list_url(), data=self.body(profile_id=foreign_profile.id), format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("device_profile", response.data)

    def test_authentication_is_required(self):
        self.client.credentials()
        self.assertEqual(self.get(self.list_url()).status_code, 401)


class AlarmRuleBulkTest(AlarmRuleAPITestCase):
    def url(self):
        return reverse("alarms:rule-bulk")

    def test_bulk_updates_creates_and_deletes_matching_by_type(self):
        kept = row(device_offline_rule(minutes=10))
        row(temperature_rule())  # missing from the payload below

        payload = {
            "device_profile": PROFILE_ID,
            "alarms": [device_offline_rule(minutes=3), gateway_offline_rule()],
        }
        response = self.post(self.url(), data=payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual({rule["alarmType"] for rule in response.data}, {"Device Offline", "Gateway Offline"})

        kept.refresh_from_db()
        # Same row, so the id and the audit trail survive a bulk save.
        self.assertEqual(kept.create_rules["MAJOR"]["condition"]["spec"]["predicate"]["defaultValue"], 3)
        self.assertFalse(AlarmRule.objects.filter(alarm_type="High Temperature").exists())
        self.assertEqual(AlarmRule.objects.count(), 2)

    def test_bulk_rejects_duplicate_types(self):
        payload = {"device_profile": PROFILE_ID, "alarms": [device_offline_rule(), device_offline_rule()]}

        response = self.post(self.url(), data=payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(AlarmRule.objects.exists())

    def test_bulk_with_an_empty_list_clears_the_profile(self):
        row(device_offline_rule())

        response = self.post(self.url(), data={"device_profile": PROFILE_ID, "alarms": []}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(AlarmRule.objects.exists())


class AlarmRulePreviewTest(AlarmRuleAPITestCase):
    def test_an_omitted_body_previews_the_stored_rules(self):
        row(device_offline_rule())
        row(gateway_offline_rule(), enabled=False)

        response = self.post(reverse("alarms:rule-preview"), data={"device_profile": PROFILE_ID}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("device_count", response.data)
        # Only the enabled rule: the preview answers "what would run".
        self.assertEqual([alarm["alarmType"] for alarm in response.data["alarms"]], ["Device Offline"])


class DisabledRuleTest(AlarmTestCase):
    """``enabled`` is the switch the old JSON-in-profile layout could not offer."""

    def test_a_disabled_rule_never_fires(self):
        self.set_rules(offline_rule(minutes=0), enabled=False)
        self.set_attribute("active", False)

        evaluate(now=timezone.now() + timedelta(minutes=1))

        self.assertFalse(Alarm.objects.exists())

    def test_the_same_rule_fires_once_enabled(self):
        self.set_rules(offline_rule(minutes=0))
        self.set_attribute("active", False)

        evaluate(now=timezone.now() + timedelta(minutes=1))

        self.assertEqual(Alarm.objects.count(), 1)


class AlarmRuleTemplateTest(AlarmRuleAPITestCase):
    """Where the front end gets a starting rule from."""

    def url(self):
        return reverse("alarms:rule-templates")

    def test_the_catalogue_is_offered(self):
        response = self.get(self.url())

        self.assertEqual(response.status_code, 200)
        ids = [template["id"] for template in response.data["results"]]
        self.assertEqual(ids, ["device-offline", "gateway-offline", "high-temperature", "low-temperature"])

        template = response.data["results"][0]
        self.assertEqual(set(template), {"id", "name", "description", "requires", "rule"})
        self.assertEqual(template["rule"]["alarmType"], "Device Offline")
        # The builder greys out a template whose keys this tenant never reports.
        self.assertIn("notifyOnOffline", template["requires"]["attributes"])

    def test_a_template_can_be_posted_as_a_rule_unchanged(self):
        template = self.get(self.url()).data["results"][2]

        response = self.post(self.list_url(), data={"device_profile": PROFILE_ID, **template["rule"]}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(AlarmRule.objects.get().alarm_type, "High Temperature")

    def test_every_template_is_a_fresh_copy(self):
        first, second = catalogue(), catalogue()
        first[0]["rule"]["alarmType"] = "Edited"
        self.assertEqual(second[0]["rule"]["alarmType"], "Device Offline")

    def test_authentication_is_required(self):
        self.client.credentials()
        self.assertEqual(self.get(self.url()).status_code, 401)

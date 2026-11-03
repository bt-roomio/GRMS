from unittest.mock import patch

from django.urls import reverse

from main.models import Device
from services.models import MappingProfile
from services.tests.test_mapping_api import (
    DEVICE_ID,
    DIMMER,
    FAN_SPEED,
    HOTEZA_INTEGRATION_ID,
    OTHER_TENANT_ID,
    ROOM_ID,
    MappingTestCase,
)
from services.tests.test_mapping_composite import FCU_MODE
from services.tests.test_mapping_composite_tags import CompositeTagTestCase, other_device_in_room
from shuttle.models import AttributeKv

URL = reverse("services:mapping-test")


class MappingTestAPITestCase(MappingTestCase):
    def run_test(self, body, status=200):
        response = self.post(URL, body, format="json")
        self.assertEqual(response.status_code, status, response.data)
        return response.data


class InlinePlainRuleTest(MappingTestAPITestCase):
    def test_to_external(self):
        report = self.run_test({"rule": FAN_SPEED, "direction": "to_external", "value": "Medium"})
        self.assertTrue(report["success"])
        self.assertEqual(report["result"], 2)
        self.assertEqual(report["input"], "Medium")
        self.assertEqual(report["rule"], {"source": "inline"})

    def test_to_external_converts_tag_ranges(self):
        body = {"rule": DIMMER, "direction": "to_external", "value": 47, "tag_ranges": ["0-100"]}
        report = self.run_test(body)
        self.assertEqual((report["result"], report["tag_ranges"]), (50, ["0-100"]))

    def test_to_grms(self):
        report = self.run_test({"rule": FAN_SPEED, "direction": "to_grms", "value": 3})
        self.assertEqual(report["result"], "High")

    def test_to_grms_out_of_tag_ranges(self):
        rule = {**DIMMER, "on_invalid": "reject"}
        report = self.run_test({"rule": rule, "direction": "to_grms", "value": 80, "tag_ranges": ["0-50"]})
        self.assertFalse(report["success"])
        self.assertEqual(report["errors"][0]["code"], "invalid")

    def test_unmapped_and_wrong_type(self):
        self.assertEqual(
            self.run_test({"rule": FAN_SPEED, "direction": "to_grms", "value": 9})["errors"][0]["code"], "unmapped"
        )
        error = self.run_test({"rule": FAN_SPEED, "direction": "to_grms", "value": "x"})["errors"][0]
        self.assertEqual((error["code"], error["field"]), ("type", "value"))

    def test_skip(self):
        rule = {**DIMMER, "on_invalid": "skip"}
        report = self.run_test({"rule": rule, "direction": "to_grms", "value": 150, "tag_ranges": ["0-100"]})
        self.assertTrue(report["skipped"])

    def test_passthrough_and_linear(self):
        passthrough = {"tag_names": ["t"], "external": {"value_type": "number"}, "transform": {"type": "passthrough"}}
        self.assertEqual(
            self.run_test({"rule": passthrough, "direction": "to_external", "value": "21.5"})["result"], 21.5
        )
        linear = {**passthrough, "transform": {"type": "linear", "ops": [{"op": "divide", "value": 10}]}}
        self.assertEqual(self.run_test({"rule": linear, "direction": "to_grms", "value": 22})["result"], 220)

    def test_unsupported_direction_of_the_rule(self):
        rule = {**FAN_SPEED, "direction": "to_grms"}
        error = self.run_test({"rule": rule, "direction": "to_external", "value": "Low"})["errors"][0]
        self.assertEqual((error["code"], error["field"]), ("direction", "direction"))

    def test_config_errors_by_field(self):
        rule = {**DIMMER, "transform": {**DIMMER["transform"], "grms": {"min": 5, "max": 1}}}
        report = self.run_test({"rule": rule, "direction": "to_external", "value": 1})
        self.assertFalse(report["success"])
        self.assertEqual(report["errors"][0]["field"], "rule.transform.grms.min")
        self.assertEqual(report["errors"][0]["code"], "config")

    def test_bad_request(self):
        self.run_test({"rule": FAN_SPEED, "direction": "sideways", "value": 1}, status=400)
        self.run_test({"direction": "to_grms", "value": 1}, status=400)
        self.run_test({"rule": FAN_SPEED, "composite_rule": FCU_MODE, "direction": "to_grms", "value": 1}, status=400)
        self.run_test({"rule": FAN_SPEED, "direction": "to_grms"}, status=400)


class InlineCompositeRuleTest(MappingTestAPITestCase):
    def test_to_external(self):
        body = {"composite_rule": FCU_MODE, "direction": "to_external", "inputs": {"power": 1, "mode": "Heat"}}
        report = self.run_test(body)
        self.assertEqual(report["result"], 1)

    def test_missing_input_skipped_with_reason(self):
        body = {"composite_rule": FCU_MODE, "direction": "to_external", "inputs": {"power": 1}}
        report = self.run_test(body)
        self.assertTrue(report["skipped"])
        self.assertEqual(report["warnings"][0]["code"], "missing_input")

    def test_missing_input_rejected(self):
        rule = {**FCU_MODE, "on_missing": "reject"}
        report = self.run_test({"composite_rule": rule, "direction": "to_external", "inputs": {"power": 1}})
        self.assertFalse(report["success"])
        self.assertEqual(report["errors"][0]["field"], "inputs.mode")

    def test_to_grms_lists_actions(self):
        report = self.run_test({"composite_rule": FCU_MODE, "direction": "to_grms", "value": 2})
        self.assertEqual([(a["alias"], a["value"]) for a in report["actions"]], [("mode", "Cool"), ("power", 1)])

    def test_conflict_by_field(self):
        rule = {**FCU_MODE, "conditions": [*FCU_MODE["conditions"], {"when": {"mode": "Cool"}, "value": 1}]}
        report = self.run_test({"composite_rule": rule, "direction": "to_grms", "value": 2})
        self.assertEqual(report["errors"][0]["field"], "composite_rule.conditions[3]")
        self.assertEqual(report["errors"][0]["code"], "conflict")

    def test_unknown_alias_warning(self):
        body = {"composite_rule": FCU_MODE, "direction": "to_external", "inputs": {"power": 0, "fan": 1}}
        self.assertEqual(self.run_test(body)["warnings"][0]["field"], "inputs.fan")


class SavedRuleTest(MappingTestAPITestCase):
    def setUp(self):
        super().setUp()
        self.profile = self.create_profile()
        MappingProfile.objects.filter(pk=self.profile["id"]).update(composite_rules=[FCU_MODE])

    def test_profile_plain_rule(self):
        body = {"profile": self.profile["id"], "tag_name": "fanSpeed", "direction": "to_grms", "value": 1}
        report = self.run_test(body)
        self.assertEqual(report["result"], "Low")
        self.assertEqual(report["rule"]["source"], "profile")

    def test_profile_composite_rule(self):
        body = {"profile": self.profile["id"], "composite_id": "fcumode", "direction": "to_grms", "value": 0}
        self.assertEqual(len(self.run_test(body)["actions"]), 1)

    def test_rule_not_found(self):
        body = {"profile": self.profile["id"], "tag_name": "nope", "direction": "to_grms", "value": 1}
        self.assertIn("tag_name", self.run_test(body, status=400))
        body = {"profile": self.profile["id"], "composite_id": "nope", "direction": "to_grms", "value": 1}
        self.assertIn("composite_id", self.run_test(body, status=400))

    def test_profile_needs_a_name(self):
        self.run_test({"profile": self.profile["id"], "direction": "to_grms", "value": 1}, status=400)

    def test_other_tenants_profile_is_404(self):
        MappingProfile.objects.filter(pk=self.profile["id"]).update(tenant_id=OTHER_TENANT_ID)
        body = {"profile": self.profile["id"], "tag_name": "fanSpeed", "direction": "to_grms", "value": 1}
        self.run_test(body, status=404)

    def test_integration_effective_rule(self):
        self.attach_profile(self.profile["id"])
        scoped = self.create_profile(
            {
                "name": "room-101",
                "integrator": "hoteza",
                "scope": "device",
                "device": DEVICE_ID,
                "rules": [{**FAN_SPEED, "transform": {"type": "enum", "map": [{"grms": "Low", "external": 10}]}}],
            }
        )
        body = {"integration": HOTEZA_INTEGRATION_ID, "tag_name": "fanSpeed", "direction": "to_grms", "value": 10}
        self.assertFalse(self.run_test(body)["success"])  # the tenant rule has no 10
        report = self.run_test({**body, "device": DEVICE_ID})
        self.assertEqual(report["result"], "Low")
        self.assertEqual(report["rule"]["scope"], "device")
        self.assertTrue(scoped["id"])


@patch("services.utils.tag_write.prepare_mqtt_request")
class RoomContextTest(CompositeTagTestCase):
    """Live inputs and write targets from the room, with no RPC and no change to any tag."""

    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def run_test(self, body, status=200):
        response = self.post(URL, body, format="json")
        self.assertEqual(response.status_code, status, response.data)
        return response.data

    def test_live_inputs(self, rpc):
        body = {
            "integration": HOTEZA_INTEGRATION_ID,
            "composite_id": "fcumode",
            "direction": "to_external",
            "room": ROOM_ID,
        }
        report = self.run_test(body)
        self.assertEqual(report["result"], 2)
        self.assertEqual(report["input"], {"power": 1, "mode": "Cool"})
        self.assertEqual(report["unavailable"], {})

    def test_write_plan_without_rpc(self, rpc):
        body = {"composite_rule": FCU_MODE, "direction": "to_grms", "value": 1, "room": ROOM_ID}
        report = self.run_test(body)
        self.assertEqual([a["tag_id"] for a in report["actions"]], [str(self.mode.pk), str(self.power.pk)])
        rpc.assert_not_called()
        self.mode.refresh_from_db()
        self.assertEqual(self.mode.str_v, "Cool")
        self.assertEqual(AttributeKv.objects.filter(attribute_key="AC Mode").count(), 1)

    def test_write_plan_checks_tag_ranges(self, rpc):
        AttributeKv.objects.filter(attribute_key="TAG_TYPES").update(json_v=[])
        AttributeKv.objects.filter(pk=self.mode.pk).delete()
        body = {"composite_rule": FCU_MODE, "direction": "to_grms", "value": 1, "room": ROOM_ID}
        error = self.run_test(body)["errors"][0]
        self.assertEqual((error["code"], error["field"]), ("missing_input", "inputs.mode"))
        rpc.assert_not_called()


class DeviceContextTest(CompositeTagTestCase):
    """A device context picks that device's own composite rule, not a neighbour's."""

    def setUp(self):
        super().setUp()
        self.other = other_device_in_room()
        for name, device, value in (("a", DEVICE_ID, 10), ("b", self.other.pk, 20)):
            rule = {**FCU_MODE, "direction": "to_external", "actions": None}
            rule["conditions"] = [{"when": {"power": 1}, "value": value}, {"when": {"power": 0}, "value": 0}]
            profile = self.scoped_profile(name, scope="device", device=str(device))
            MappingProfile.objects.filter(pk=profile["id"]).update(composite_rules=[rule])
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def run_rule(self, device):
        body = {
            "integration": HOTEZA_INTEGRATION_ID,
            "composite_id": "fcumode",
            "direction": "to_external",
            "device": str(device),
            "inputs": {"power": 1},
        }
        response = self.post(URL, body, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_each_device_gets_its_own_rule(self):
        self.assertEqual(self.run_rule(DEVICE_ID)["result"], 10)
        self.assertEqual(self.run_rule(self.other.pk)["result"], 20)

    def test_device_without_room(self):
        Device.objects.filter(pk=self.other.pk).update(room_id=None)
        self.assertEqual(self.run_rule(self.other.pk)["result"], 20)

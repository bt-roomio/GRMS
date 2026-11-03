import copy
from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse

from main.models import Device, Room
from services.consumers.tags import RoomTagsConsumer, TagDetailConsumer
from services.models import Integration, MappingProfile
from services.tests.test_mapping_api import DEVICE_ID, HOTEZA_INTEGRATION_ID, ROOM_ID, ROOM_TYPE_ID, TENANT_ID
from services.tests.test_mapping_composite import FCU_MODE
from services.tests.test_mapping_tags import (
    RPC_OK,
    TagMappingTestCase,
    tag_type_entry,
)
from services.utils.composite_tags import virtual_tag_id, virtual_tag_room_id
from shuttle.models import AttributeKv, TsKvDictionary, TsKvLatest

RPC_FAILED = {"device": "fcu", "data": {"success": False, "msg": "Timeout error"}}


class CompositeTagTestCase(TagMappingTestCase):
    """Room 101 has ``AC ON OFF`` = 1 and ``AC Mode`` = "Cool" on its device; the integration's
    profile makes them ``fcumode`` (0 off, 1 heat, 2 cool)."""

    def setUp(self):
        super().setUp()
        self.power = self.attribute("AC ON OFF", long_v=1)
        self.mode = self.attribute("AC Mode", str_v="Cool")
        AttributeKv.objects.filter(attribute_key="TAG_TYPES").update(
            json_v=[
                tag_type_entry("fanSpeed", "FCUSPEED", ["Low", "Medium", "High"]),
                tag_type_entry("AC Mode", "FCUMODE", ["Heat", "Cool", "Fan"]),
                tag_type_entry("AC ON OFF", "SWITCH", [0, 1]),
            ]
        )
        self.set_composites(self.profile["id"], FCU_MODE)
        self.virtual_id = virtual_tag_id(ROOM_ID, "fcumode")

    @staticmethod
    def set_composites(profile_id, *rules):
        MappingProfile.objects.filter(pk=profile_id).update(composite_rules=list(rules))

    def fcumode(self):
        return self.room_tags()["fcumode"]


class CompositeReadTest(CompositeTagTestCase):
    def test_virtual_tag_in_room_tags(self):
        tag = self.fcumode()
        self.assertEqual(tag["id"], self.virtual_id)
        self.assertEqual(tag["value"], 2)
        self.assertEqual(tag["tag_ranges"], [0, 1, 2])
        self.assertTrue(tag["virtual"])
        self.assertIsNotNone(tag["updated_at"])
        # The inputs stay tags of their own.
        self.assertEqual(self.room_tags()["AC Mode"]["value"], "Cool")

    def test_any_input_change_recomputes(self):
        AttributeKv.objects.filter(pk=self.power.pk).update(long_v=0)
        self.assertEqual(self.fcumode()["value"], 0)
        AttributeKv.objects.filter(pk=self.power.pk).update(long_v=1)
        AttributeKv.objects.filter(pk=self.mode.pk).update(str_v="Heat")
        self.assertEqual(self.fcumode()["value"], 1)

    def test_virtual_tag_detail(self):
        tag = self.tag_by_id(self.virtual_id)
        self.assertEqual(tag["value"], 2)
        self.assertEqual(tag["tag_name"], "fcumode")

    def tag_by_id(self, tag_id):
        response = self.get(reverse("services:tag-detail", args=[tag_id]))
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_unknown_virtual_id_is_404(self):
        response = self.get(reverse("services:tag-detail", args=[virtual_tag_id(ROOM_ID, "other")]))
        self.assertEqual(response.status_code, 404)

    def test_missing_input_gives_null(self):
        self.mode.delete()
        self.assertIsNone(self.fcumode()["value"])
        AttributeKv.objects.filter(pk=self.power.pk).update(long_v=0)
        self.assertEqual(self.fcumode()["value"], 0)  # off does not depend on the mode

    def test_room_without_inputs_has_no_virtual_tag(self):
        AttributeKv.objects.filter(pk__in=[self.power.pk, self.mode.pk]).delete()
        self.assertNotIn("fcumode", self.room_tags())

    def test_telemetry_inputs(self):
        rule = copy.deepcopy(FCU_MODE)
        for item in rule["inputs"]:
            item["source"] = "telemetry"
        self.set_composites(self.profile["id"], rule)
        for name, column, value in (("AC ON OFF", "long_v", 1), ("AC Mode", "str_v", "Heat")):
            key, _ = TsKvDictionary.objects.get_or_create(key=name)
            TsKvLatest.objects.create(entity_id=DEVICE_ID, key_id=key.key_id, **{column: value})
        self.assertEqual(self.fcumode()["value"], 1)

    def test_physical_output_tag_is_computed(self):
        physical = self.attribute("fcumode", long_v=99)
        tag = self.fcumode()
        self.assertEqual(tag["id"], str(physical.pk))
        self.assertEqual(tag["value"], 2)
        self.assertNotIn("virtual", tag)
        self.assertEqual(self.tag(physical)["value"], 2)

    def test_without_profile_no_virtual_tag(self):
        Integration.objects.filter(pk=HOTEZA_INTEGRATION_ID).update(mapping_profile=None)
        self.assertNotIn("fcumode", self.room_tags())


class CompositeScopeTest(CompositeTagTestCase):
    def test_device_profile_overrides_tenant_rule(self):
        inverted = copy.deepcopy(FCU_MODE)
        inverted["conditions"][2]["value"] = 1
        inverted["conditions"][1]["value"] = 2
        inverted["actions"][1]["value"], inverted["actions"][2]["value"] = 2, 1
        profile = self.scoped_profile("room-101", scope="device", device=DEVICE_ID)
        self.set_composites(profile["id"], inverted)
        self.assertEqual(self.fcumode()["value"], 1)

    def test_room_type_profile_overrides_tenant_rule(self):
        profile = self.scoped_profile("suite", scope="room_type", room_type=ROOM_TYPE_ID)
        self.set_composites(
            profile["id"],
            {
                **FCU_MODE,
                "output": {"tag_name": "fcumode", "value_type": "string"},
                "direction": "to_external",
                "conditions": [{"when": {"power": 1}, "value": "on"}, {"when": {"power": 0}, "value": "off"}],
            },
        )
        self.assertEqual(self.fcumode()["value"], "on")

    def test_ambiguous_inputs(self):
        other = Device.objects.exclude(pk=DEVICE_ID).filter(tenant_id=TENANT_ID).first()
        assert other is not None
        Device.objects.filter(pk=other.pk).update(room_id=ROOM_ID)
        AttributeKv.objects.create(
            entity_id=other.pk,
            entity_type="DEVICE",
            attribute_type=AttributeKv.CLIENT_SCOPE,
            attribute_key="AC Mode",
            str_v="Heat",
        )
        self.assertIsNone(self.fcumode()["value"])


@patch("services.utils.tag_write.prepare_mqtt_request", return_value=RPC_OK)
class CompositeWriteTest(CompositeTagTestCase):
    def put_virtual(self, value):
        return self.put(reverse("services:tag-detail", args=[self.virtual_id]), {"value": value}, format="json")

    def test_writes_in_order(self, rpc):
        response = self.put_virtual(1)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [call.args[1:3] for call in rpc.call_args_list],
            [("setAttribute", {"AC Mode": "Heat"}), ("setAttribute", {"AC ON OFF": 1})],
        )
        self.assertTrue(response.data["success"])
        self.assertEqual([a["status"] for a in response.data["actions"]], ["ok", "ok"])
        self.assertEqual(response.data["tag"]["value"], 1)
        self.mode.refresh_from_db()
        self.assertEqual(self.mode.str_v, "Heat")

    def test_unknown_value_sends_nothing(self, rpc):
        response = self.put_virtual(7)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "unmapped")
        rpc.assert_not_called()

    def test_value_outside_tag_ranges_sends_nothing(self, rpc):
        AttributeKv.objects.filter(attribute_key="TAG_TYPES").update(
            json_v=[tag_type_entry("AC Mode", "FCUMODE", ["Fan"])]
        )
        response = self.put_virtual(2)
        self.assertEqual(response.status_code, 400)
        self.assertEqual((response.data["code"], response.data["field"]), ("invalid", "set.mode"))
        rpc.assert_not_called()

    def test_failed_required_write_stops_the_rest(self, rpc):
        rpc.side_effect = [RPC_OK, RPC_FAILED]
        response = self.put_virtual(1)
        self.assertEqual(response.status_code, 502, response.data)
        self.assertFalse(response.data["success"])
        self.assertTrue(response.data["partial"])
        self.assertEqual([a["status"] for a in response.data["actions"]], ["ok", "failed"])
        self.power.refresh_from_db()
        self.assertEqual(self.power.long_v, 1)  # unchanged: the device refused

    def test_not_run_after_failure(self, rpc):
        rpc.return_value = RPC_FAILED
        response = self.put_virtual(2)
        self.assertEqual(response.status_code, 502)
        self.assertFalse(response.data["partial"])
        self.assertEqual([a["status"] for a in response.data["actions"]], ["failed", "not_run"])
        self.assertEqual(rpc.call_count, 1)

    def test_optional_write_failure_still_succeeds(self, rpc):
        rule = copy.deepcopy(FCU_MODE)
        rule["actions"][2]["set"][0]["required"] = False
        self.set_composites(self.profile["id"], rule)
        rpc.side_effect = [RPC_FAILED, RPC_OK]
        response = self.put_virtual(2)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([a["status"] for a in response.data["actions"]], ["failed", "ok"])

    def test_skip(self, rpc):
        self.set_composites(self.profile["id"], {**FCU_MODE, "on_no_match": "skip"})
        response = self.put_virtual(7)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["skipped"])
        rpc.assert_not_called()

    def test_reads_only_rule_rejects_writes(self, rpc):
        self.set_composites(self.profile["id"], {**FCU_MODE, "direction": "to_external", "actions": None})
        response = self.put_virtual(1)
        self.assertEqual(response.data["code"], "direction")
        rpc.assert_not_called()

    def test_plain_tags_still_written(self, rpc):
        response = self.put_tag(self.fan, 3)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(rpc.call_args.args[2], {"fanSpeed": "High"})


class CompositeConsumerTest(CompositeTagTestCase):
    def consumer(self, consumer_class):
        integration = Integration.objects.select_related("tenant").get(pk=HOTEZA_INTEGRATION_ID)
        consumer = consumer_class()
        consumer.scope = {"integration": integration, "tenant": integration.tenant}
        return consumer

    def test_room_tags_payload_has_virtual_tag(self):
        payload, _ = self.consumer(RoomTagsConsumer).build_payload({"room_id": ROOM_ID})
        tags = {tag["tag_name"]: tag for tag in payload["results"]}
        self.assertEqual(tags["fcumode"]["value"], 2)

    def test_virtual_tag_watches_its_inputs(self):
        payload, watch = self.consumer(TagDetailConsumer).build_payload(self.virtual_id)
        self.assertEqual(payload["value"], 2)
        self.assertIn(DEVICE_ID, watch["entity_ids"])
        self.assertTrue({"AC ON OFF", "AC Mode"} <= watch["tag_names"])
        self.assertTrue(watch["composite"])


class CompositeProfileAPITest(TagMappingTestCase):
    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def put_profile(self, body):
        url = reverse("services:mapping-profile-detail", args=[self.profile["id"]])
        return self.put(url, body, format="json")

    def body(self, **fields):
        return {"name": "Hoteza", "integrator": "hoteza", "rules": self.profile["rules"], **fields}

    def test_saved_and_read(self):
        response = self.put_profile(self.body(composite_rules=[FCU_MODE]))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["composite_rules"][0]["id"], "fcumode")

    def test_left_out_of_put_stays(self):
        self.put_profile(self.body(composite_rules=[FCU_MODE]))
        response = self.put_profile(self.body())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["composite_rules"]), 1)

    def test_errors_by_rule_and_field(self):
        rule = copy.deepcopy(FCU_MODE)
        rule["conditions"][0]["when"]["speed"] = 1
        response = self.put_profile(self.body(composite_rules=[FCU_MODE, rule]))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["composite_rules"][0], {})
        self.assertIn("conditions[0].when.speed", response.data["composite_rules"][1])

    def test_repeated_ids(self):
        response = self.put_profile(self.body(composite_rules=[FCU_MODE, FCU_MODE]))
        self.assertEqual(response.status_code, 400)
        self.assertIn("repeat", str(response.data["composite_rules"][0]))

    def test_output_with_plain_rule(self):
        rule = {**FCU_MODE, "output": {"tag_name": "fanSpeed", "value_type": "integer"}}
        response = self.put_profile(self.body(composite_rules=[rule]))
        self.assertEqual(response.status_code, 400)

    def test_old_profiles_have_none(self):
        self.assertEqual(self.profile["composite_rules"], [])


def other_device_in_room():
    """A second device of the tenant, moved into room 101."""
    other = Device.objects.exclude(pk=DEVICE_ID).filter(tenant_id=TENANT_ID).first()
    assert other is not None
    Device.objects.filter(pk=other.pk).update(room_id=ROOM_ID)
    return other


def client_attribute(device_id, key, **value):
    return AttributeKv.objects.create(
        entity_id=device_id, entity_type="DEVICE", attribute_type=AttributeKv.CLIENT_SCOPE, attribute_key=key, **value
    )


class CompositeReviewFixesTest(CompositeTagTestCase):
    def test_virtual_id_gives_its_room_back(self):
        self.assertEqual(str(virtual_tag_room_id(self.virtual_id, "fcumode")), ROOM_ID)

    def test_tag_of_inactive_room_stays_plain(self):
        physical = self.attribute("fcumode", long_v=99)
        Room.objects.filter(pk=ROOM_ID).update(active=False)
        self.assertEqual(self.tag(physical)["value"], 99)

    def test_one_rule_per_output_name_across_scopes(self):
        heat_only = {
            **FCU_MODE,
            "id": "fcumode-suite",
            "direction": "to_external",
            "actions": None,
            "conditions": [{"when": {"power": 1}, "value": 7}, {"when": {"power": 0}, "value": 0}],
        }
        profile = self.scoped_profile("suite", scope="room_type", room_type=ROOM_TYPE_ID)
        self.set_composites(profile["id"], heat_only)
        named = [tag for tag in self.room_tags_list() if tag["tag_name"] == "fcumode"]
        self.assertEqual(len(named), 1)
        self.assertEqual(named[0]["value"], 7)

    def test_device_rule_does_not_repeat_a_name_of_another_device(self):
        other = other_device_in_room()
        client_attribute(other.pk, "fcumode", long_v=5)
        profile = self.scoped_profile("room-101", scope="device", device=DEVICE_ID)
        self.set_composites(profile["id"], FCU_MODE)
        self.set_composites(self.profile["id"])
        named = [tag for tag in self.room_tags_list() if tag["tag_name"] == "fcumode"]
        self.assertEqual([tag["value"] for tag in named], [5])

    def test_computed_physical_tag_takes_the_inputs_time(self):
        physical = self.attribute("fcumode", long_v=99)
        AttributeKv.objects.filter(pk=physical.pk).update(last_update_ts=1_000)
        AttributeKv.objects.filter(pk=self.mode.pk).update(last_update_ts=1_800_000_000_000)
        tag = self.fcumode()
        self.assertTrue(tag["updated_at"].startswith("2027-01-15"), tag["updated_at"])

    def room_tags_list(self):
        response = self.get(reverse("services:tags-by-room-list", args=[ROOM_ID]))
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["results"]


@patch("services.utils.tag_write.prepare_mqtt_request", return_value=RPC_OK)
class CompositeWriteLockTest(CompositeTagTestCase):
    def test_concurrent_write_answers_409(self, rpc):
        lock = f"services:composite-write:{self.virtual_id}"
        cache.set(lock, 1, 60)
        try:
            response = self.put(reverse("services:tag-detail", args=[self.virtual_id]), {"value": 1}, format="json")
        finally:
            cache.delete(lock)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "busy")
        rpc.assert_not_called()

    def test_lock_is_released(self, rpc):
        url = reverse("services:tag-detail", args=[self.virtual_id])
        self.assertEqual(self.put(url, {"value": 1}, format="json").status_code, 200)
        self.assertEqual(self.put(url, {"value": 2}, format="json").status_code, 200)

    def test_plain_tag_error_has_field(self, rpc):
        response = self.put_tag(self.fan, 9)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["field"], "value")

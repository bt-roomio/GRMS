from unittest.mock import patch

from django.urls import reverse

from main.models import Device, Room
from services.consumers.tags import RoomTagsConsumer, TagDetailConsumer
from services.models import Integration, Integrator, MappingRule
from services.tests.test_mapping_api import (
    DEVICE_ID,
    DIMMER,
    HOTEZA_INTEGRATION_ID,
    ROOM_ID,
    ROOM_TYPE_ID,
    TENANT_ID,
    MappingTestCase,
    fan_speed_with_medium,
    profile_body,
)
from shuttle.models import AttributeKv

CLIENT_TOKEN = "hoteza-client"
ACCESS_TOKEN = "hoteza-access"
RPC_OK = {"success": True}


def tag_type_entry(tag_name, tag_type, tag_ranges):
    return {
        "tag_section": "ATTRIBUTE",
        "tag_sub_section": AttributeKv.CLIENT_SCOPE,
        "tag_name": tag_name,
        "tag_type": tag_type,
        "tag_ranges": tag_ranges,
    }


class TagMappingTestCase(MappingTestCase):
    """Tags of the fixture device in room 101: ``fanSpeed`` (enum 1..3) and ``dimmer`` (0..100 in
    steps of 10), read through the Hoteza integration's tokens. Rules match tags by ``tag_name``."""

    def setUp(self):
        super().setUp()
        Integrator.objects.filter(pk="hoteza").update(client_id=CLIENT_TOKEN)
        Integration.objects.filter(pk=HOTEZA_INTEGRATION_ID).update(access_token=ACCESS_TOKEN)
        Room.objects.filter(pk=ROOM_ID).update(type_id=ROOM_TYPE_ID)
        self.profile = self.create_profile()
        self.attach_profile(self.profile["id"])

        self.fan = self.attribute("fanSpeed", str_v="Medium")
        self.dimmer = self.attribute("dimmer", long_v=47)
        self.attribute(
            "TAG_TYPES",
            scope=AttributeKv.SERVER_SCOPE,
            json_v=[
                tag_type_entry("fanSpeed", "FCUSPEED", ["Low", "Medium", "High"]),
                tag_type_entry("dimmer", "Light Dimmer", ["0-100"]),
            ],
        )
        self.client.credentials(HTTP_CLIENTTOKEN=CLIENT_TOKEN, HTTP_ACCESSTOKEN=ACCESS_TOKEN)

    @staticmethod
    def attribute(key, scope=AttributeKv.CLIENT_SCOPE, **value):
        return AttributeKv.objects.create(
            entity_id=DEVICE_ID, entity_type="DEVICE", attribute_type=scope, attribute_key=key, **value
        )

    def scoped_profile(self, name, *rules, **scope):
        # Created with the JWT client: the tag requests use the integration's tokens.
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)
        profile = self.create_profile(profile_body(*rules, name=name, **scope))
        self.client.credentials(HTTP_CLIENTTOKEN=CLIENT_TOKEN, HTTP_ACCESSTOKEN=ACCESS_TOKEN)
        return profile

    def room_tags(self):
        response = self.get(reverse("services:tags-by-room-list", args=[ROOM_ID]))
        self.assertEqual(response.status_code, 200, response.data)
        assert response.data is not None
        return {tag["tag_name"]: tag for tag in response.data["results"]}

    def tag(self, tag):
        response = self.get(reverse("services:tag-detail", args=[tag.pk]))
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def put_tag(self, tag, value):
        return self.put(reverse("services:tag-detail", args=[tag.pk]), {"value": value}, format="json")


class TagReadMappingTest(TagMappingTestCase):
    def test_room_tags_in_integrator_form(self):
        tags = self.room_tags()
        self.assertEqual(tags["fanSpeed"]["value"], 2)
        self.assertEqual(tags["fanSpeed"]["tag_ranges"], [1, 2, 3])
        self.assertEqual(tags["fanSpeed"]["tag_type"], "FCUSPEED")
        self.assertEqual(tags["dimmer"]["value"], 50)
        self.assertEqual(tags["dimmer"]["tag_ranges"], ["0-100"])

    def test_tag_detail_in_integrator_form(self):
        self.assertEqual(self.tag(self.fan)["value"], 2)
        self.assertEqual(self.tag(self.fan)["tag_ranges"], [1, 2, 3])

    def test_without_profile_values_stay(self):
        Integration.objects.filter(pk=HOTEZA_INTEGRATION_ID).update(mapping_profile=None)
        tags = self.room_tags()
        self.assertEqual(tags["fanSpeed"]["value"], "Medium")
        self.assertEqual(tags["fanSpeed"]["tag_ranges"], ["Low", "Medium", "High"])

    def test_tag_without_rule_stays(self):
        self.attribute("mode", str_v="Medium")
        self.assertEqual(self.room_tags()["mode"]["value"], "Medium")

    def test_rule_does_not_need_tag_types_entry(self):
        AttributeKv.objects.filter(attribute_key="TAG_TYPES").update(json_v=[])
        tag = self.room_tags()["fanSpeed"]
        self.assertEqual(tag["value"], 2)
        self.assertIsNone(tag["tag_type"])
        self.assertIsNone(tag["tag_ranges"])

    def test_tags_of_one_type_on_one_device_convert_apart(self):
        dimmer_2 = self.attribute("dimmer_2", long_v=128)
        AttributeKv.objects.filter(attribute_key="TAG_TYPES").update(
            json_v=[
                tag_type_entry("dimmer", "Light Dimmer", ["0-100"]),
                tag_type_entry("dimmer_2", "Light Dimmer", ["0-255"]),
            ]
        )
        MappingRule.objects.create(
            profile_id=self.profile["id"],
            tag_name="dimmer_2",
            external=DIMMER["external"],
            transform={**DIMMER["transform"], "grms": {"min": 0, "max": 255}},
        )
        tags = self.room_tags()
        self.assertEqual(tags["dimmer"]["value"], 50)
        self.assertEqual(tags["dimmer_2"]["value"], 50)
        self.assertEqual(self.tag(dimmer_2)["value"], 50)

    def test_unmapped_stored_value_goes_out_as_null(self):
        AttributeKv.objects.filter(pk=self.fan.pk).update(str_v="Turbo")
        self.assertIsNone(self.room_tags()["fanSpeed"]["value"])


class ScopedProfileMappingTest(TagMappingTestCase):
    """A tag takes its rule from the device profile, then the room type profile, then the
    integration's profile."""

    def test_most_specific_profile_wins(self):
        self.assertEqual(self.room_tags()["fanSpeed"]["value"], 2)
        self.scoped_profile("suite", fan_speed_with_medium(20), scope="room_type", room_type=ROOM_TYPE_ID)
        self.assertEqual(self.room_tags()["fanSpeed"]["value"], 20)
        self.scoped_profile("room-101", fan_speed_with_medium(40), scope="device", device=DEVICE_ID)
        self.assertEqual(self.room_tags()["fanSpeed"]["value"], 40)
        self.assertEqual(self.tag(self.fan)["value"], 40)

    def test_tag_without_rule_in_scoped_profile_falls_back(self):
        self.scoped_profile("room-101", fan_speed_with_medium(40), scope="device", device=DEVICE_ID)
        tags = self.room_tags()
        self.assertEqual(tags["fanSpeed"]["value"], 40)
        self.assertEqual(tags["dimmer"]["value"], 50)  # from the integration's profile

    def test_profiles_of_other_targets_do_not_apply(self):
        other_device = Device.objects.exclude(pk=DEVICE_ID).filter(tenant_id=TENANT_ID).first()
        assert other_device is not None
        self.scoped_profile("other", fan_speed_with_medium(99), scope="device", device=other_device.pk)
        self.assertEqual(self.room_tags()["fanSpeed"]["value"], 2)

    def test_profiles_of_another_integrator_do_not_apply(self):
        self.scoped_profile("test-101", fan_speed_with_medium(99), integrator="Test", scope="device", device=DEVICE_ID)
        self.assertEqual(self.room_tags()["fanSpeed"]["value"], 2)

    def test_scoped_profiles_need_the_integration_profile(self):
        self.scoped_profile("room-101", fan_speed_with_medium(40), scope="device", device=DEVICE_ID)
        Integration.objects.filter(pk=HOTEZA_INTEGRATION_ID).update(mapping_profile=None)
        self.assertEqual(self.room_tags()["fanSpeed"]["value"], "Medium")

    @patch("services.views.tags.prepare_mqtt_request", return_value=RPC_OK)
    def test_write_uses_scoped_rule(self, rpc):
        self.scoped_profile("room-101", fan_speed_with_medium(40), scope="device", device=DEVICE_ID)
        response = self.put_tag(self.fan, 40)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(rpc.call_args.args[2], {"fanSpeed": "Medium"})


@patch("services.views.tags.prepare_mqtt_request", return_value=RPC_OK)
class TagWriteMappingTest(TagMappingTestCase):
    def test_value_written_in_grms_form(self, rpc):
        response = self.put_tag(self.fan, 3)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(rpc.call_args.args[1:], ("setAttribute", {"fanSpeed": "High"}, 5))
        self.fan.refresh_from_db()
        self.assertEqual(self.fan.str_v, "High")
        self.assertEqual(response.data["tag"]["value"], 3)

    def test_range_value_converted(self, rpc):
        response = self.put_tag(self.dimmer, 70)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(rpc.call_args.args[2], {"dimmer": 70})

    def test_unmapped_value_rejected(self, rpc):
        response = self.put_tag(self.fan, 4)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "unmapped")
        rpc.assert_not_called()

    def test_value_of_wrong_type_rejected(self, rpc):
        response = self.put_tag(self.fan, "fast")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "type")
        rpc.assert_not_called()

    def test_clamp_out_of_range_value(self, rpc):
        response = self.put_tag(self.dimmer, 150)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(rpc.call_args.args[2], {"dimmer": 100})

    def test_skip_leaves_tag_unchanged(self, rpc):
        MappingRule.objects.filter(profile_id=self.profile["id"], tag_name="dimmer").update(on_invalid="skip")
        response = self.put_tag(self.dimmer, 150)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["skipped"])
        self.assertIsNone(response.data["rpc"])
        rpc.assert_not_called()
        self.dimmer.refresh_from_db()
        self.assertEqual(self.dimmer.long_v, 47)

    def test_const_writes_its_value(self, rpc):
        MappingRule.objects.filter(profile_id=self.profile["id"], tag_name="fanSpeed").update(
            on_invalid="const", on_invalid_value="Low"
        )
        response = self.put_tag(self.fan, 9)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(rpc.call_args.args[2], {"fanSpeed": "Low"})

    def test_without_profile_value_written_as_is(self, rpc):
        Integration.objects.filter(pk=HOTEZA_INTEGRATION_ID).update(mapping_profile=None)
        response = self.put_tag(self.fan, "Low")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(rpc.call_args.args[2], {"fanSpeed": "Low"})


class ConsumerMappingTest(TagMappingTestCase):
    """The WebSocket payloads go through the same mapping as the REST responses."""

    def consumer(self, consumer_class):
        integration = Integration.objects.select_related("tenant").get(pk=HOTEZA_INTEGRATION_ID)
        consumer = consumer_class()
        consumer.scope = {"integration": integration, "tenant": integration.tenant}
        return consumer

    def test_room_tags_payload(self):
        payload, _ = self.consumer(RoomTagsConsumer).build_payload({"room_id": ROOM_ID})
        tags = {tag["tag_name"]: tag for tag in payload["results"]}
        self.assertEqual(tags["fanSpeed"]["value"], 2)
        self.assertEqual(tags["dimmer"]["value"], 50)

    def test_profile_change_applies_without_reconnect(self):
        consumer = self.consumer(RoomTagsConsumer)
        Integration.objects.filter(pk=HOTEZA_INTEGRATION_ID).update(mapping_profile=None)
        payload, _ = consumer.build_payload({"room_id": ROOM_ID})
        tags = {tag["tag_name"]: tag for tag in payload["results"]}
        self.assertEqual(tags["fanSpeed"]["value"], "Medium")

    def test_tag_payload(self):
        payload, _, _ = self.consumer(TagDetailConsumer).build_payload(self.fan.pk)
        self.assertEqual(payload["value"], 2)
        self.assertEqual(payload["tag_ranges"], [1, 2, 3])

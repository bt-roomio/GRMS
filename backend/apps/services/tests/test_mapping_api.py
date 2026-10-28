from django.urls import reverse

from core.tests.base import BaseTestCase
from services.models import Integration, MappingOverride, MappingProfile, TagType, TagTypeGroup

TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"  # admin@gmail.com's tenant
OTHER_TENANT_ID = "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc"
HOTEZA_INTEGRATION_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
ROOM_TYPE_ID = "deb5db89-b9cf-4aee-989d-4a7a7bdeb096"
ROOM_ID = "df77f910-2dcd-45cf-b6be-054c744561a7"
DEVICE_ID = "47aef21b-6cc9-4ec5-8573-1a6f491940c0"

FAN_SPEED = {
    "id": "fan_speed",
    "tag_type": "FCUSPEED",
    "external": {"value_type": "integer"},
    "transform": {
        "type": "enum",
        "map": [{"grms": "Low", "external": 1}, {"grms": "Medium", "external": 2}, {"grms": "High", "external": 3}],
    },
}
DIMMER = {
    "id": "dimmer",
    "tag_type": "Light Dimmer",
    "external": {"value_type": "integer"},
    "transform": {"type": "range", "grms": {"min": 0, "max": 100}, "external": {"min": 0, "max": 100, "step": 10}},
    "on_invalid": "clamp",
}


def enum_transform(*pairs):
    return {"type": "enum", "map": [{"grms": grms, "external": external} for grms, external in pairs]}


def profile_body(*rules, code="hoteza", integrator="hoteza"):
    return {"code": code, "name": "Hoteza", "integrator": integrator, "rules": list(rules or (FAN_SPEED, DIMMER))}


def tag_type(name, ranges, tenant_id=TENANT_ID):
    group, _ = TagTypeGroup.objects.get_or_create(name="Hoteza", tenant_id=tenant_id)
    instance = TagType.objects.create(name=name, group=group, tenant_id=tenant_id)
    for value in ranges:
        instance.tag_ranges.create(range_value=value)
    return instance


class MappingTestCase(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "customer.yaml",
        "dashboard.yaml",
        "room_type.yaml",
        "room.yaml",
        "device_profile.yaml",
        "device.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "integrations.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)
        self.fan_speed = tag_type("FCUSPEED", ["Low", "Medium", "High"])
        self.dimmer = tag_type("Light Dimmer", ["0-100"])

    def create_profile(self, body=None):
        response = self.post(reverse("services:mapping-profile-list"), body or profile_body(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def attach_profile(self, profile_id):
        Integration.objects.filter(pk=HOTEZA_INTEGRATION_ID).update(mapping_profile_id=profile_id)


class MappingProfileAPITest(MappingTestCase):
    def test_create_and_list(self):
        profile = self.create_profile()
        rules = {rule["id"]: rule for rule in profile["rules"]}
        self.assertEqual(set(rules), {"fan_speed", "dimmer"})
        self.assertEqual(rules["fan_speed"]["tag_type"], "FCUSPEED")
        self.assertEqual(rules["fan_speed"]["direction"], "both")
        self.assertEqual(rules["fan_speed"]["on_invalid"], "reject")
        self.assertIsNone(rules["fan_speed"]["validate"])

        response = self.get(reverse("services:mapping-profile-list"))
        assert response.data is not None
        self.assertEqual([row["code"] for row in response.data["results"]], ["hoteza"])

    def test_rule_must_fit_its_tag_type(self):
        turbo = {**FAN_SPEED, "transform": {"type": "enum", "map": [{"grms": "Turbo", "external": 4}]}}
        response = self.post(reverse("services:mapping-profile-list"), profile_body(turbo), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Turbo", str(response.data))

        wide = {**DIMMER, "transform": {**DIMMER["transform"], "grms": {"min": 0, "max": 255}}}
        response = self.post(reverse("services:mapping-profile-list"), profile_body(wide), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("0-255", str(response.data))

    def test_rule_structure_is_validated(self):
        broken = {**DIMMER, "transform": {**DIMMER["transform"], "external": {"min": 0, "max": 100, "step": 0}}}
        response = self.post(reverse("services:mapping-profile-list"), profile_body(broken), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("step", str(response.data))

    def test_tag_type_of_another_tenant(self):
        tag_type("Foreign", [True, False], tenant_id=OTHER_TENANT_ID)
        foreign = {**FAN_SPEED, "tag_type": "Foreign"}
        response = self.post(reverse("services:mapping-profile-list"), profile_body(foreign), format="json")
        self.assertEqual(response.status_code, 400)

    def test_one_rule_per_tag_type_and_id(self):
        twin = {**FAN_SPEED, "id": "fan_speed_2"}
        response = self.post(reverse("services:mapping-profile-list"), profile_body(FAN_SPEED, twin), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Duplicate tag types", str(response.data))

    def test_code_is_unique_per_tenant(self):
        self.create_profile()
        response = self.post(reverse("services:mapping-profile-list"), profile_body(), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("code", response.data)

    def test_update_replaces_rules(self):
        profile = self.create_profile()
        url = reverse("services:mapping-profile-detail", args=[profile["id"]])
        response = self.put(url, profile_body(DIMMER), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([rule["id"] for rule in response.data["rules"]], ["dimmer"])

    def test_profile_of_another_tenant_is_hidden(self):
        profile = MappingProfile.objects.create(code="x", name="x", integrator_id="Test", tenant_id=OTHER_TENANT_ID)
        response = self.get(reverse("services:mapping-profile-detail", args=[profile.pk]))
        self.assertEqual(response.status_code, 404)

    def test_delete_detaches_integrations(self):
        profile = self.create_profile()
        self.attach_profile(profile["id"])
        response = self.delete(reverse("services:mapping-profile-detail", args=[profile["id"]]))
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(Integration.objects.get(pk=HOTEZA_INTEGRATION_ID).mapping_profile_id)

    def test_tag_type_used_by_a_rule_cannot_be_deleted(self):
        self.create_profile()
        response = self.delete(reverse("services:tag-type-detail", args=[self.fan_speed.pk]))
        self.assertEqual(response.status_code, 409)

    def test_rule_for_shared_tag_type(self):
        tag_type("SharedFan", ["Low", "High"], tenant_id=None)
        shared = {**FAN_SPEED, "tag_type": "SharedFan", "transform": enum_transform(("Low", 1), ("High", 3))}
        profile = self.create_profile(profile_body(shared))
        self.assertEqual(profile["rules"][0]["tag_type"], "SharedFan")

    def test_own_tag_type_wins_over_shared_one(self):
        # The shared FCUSPEED has no "Low": the rule passes only against the tenant's own type.
        tag_type("FCUSPEED", ["Off"], tenant_id=None)
        self.create_profile(profile_body(FAN_SPEED))

    def update_tag_type(self, ranges):
        body = {"name": "FCUSPEED", "group": str(self.fan_speed.group_id), "tag_ranges": ranges}
        return self.put(reverse("services:tag-type-detail", args=[self.fan_speed.pk]), body, format="json")

    def test_tag_type_ranges_must_keep_fitting_rules(self):
        self.create_profile()
        response = self.update_tag_type(["Medium", "High"])
        self.assertEqual(response.status_code, 400)
        self.assertIn("Low", str(response.data))
        response = self.update_tag_type(["Low", "Medium", "High", "Turbo"])
        self.assertEqual(response.status_code, 200, response.data)

    def test_tag_type_ranges_must_keep_fitting_overrides(self):
        self.attach_profile(self.create_profile()["id"])
        MappingOverride.objects.create(
            integration_id=HOTEZA_INTEGRATION_ID,
            level=MappingOverride.Level.TENANT,
            rule_overrides={"fan_speed": {"transform": enum_transform(("Low", 1), ("High", 3))}},
        )
        response = self.update_tag_type(["Medium", "High"])
        self.assertEqual(response.status_code, 400)
        self.assertIn("Override", str(response.data))


class MappingProfileTestEndpointTest(MappingTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("services:mapping-profile-test", args=[self.create_profile()["id"]])

    def run_rule(self, **body):
        return self.post(self.url, body, format="json")

    def test_to_external(self):
        response = self.run_rule(
            rule="fan_speed", direction="to_external", input="Medium", tag_ranges=["Low", "Medium", "High"]
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"output": 2, "tag_ranges": [1, 2, 3]})

    def test_to_grms(self):
        response = self.run_rule(rule="dimmer", direction="to_grms", input="55", tag_ranges=["0-100"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"output": 60})

    def test_unconvertible_value(self):
        response = self.run_rule(rule="fan_speed", direction="to_grms", input=4)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "unmapped")

    def test_unknown_rule(self):
        response = self.run_rule(rule="nope", direction="to_grms", input=1)
        self.assertEqual(response.status_code, 400)


class IntegrationMappingProfileTest(MappingTestCase):
    def put_integration(self, profile_id):
        body = {"integrator": "hoteza", "tenant": TENANT_ID, "hotel_id": "999", "mapping_profile": profile_id}
        return self.put(reverse("services:integration-detail", args=[HOTEZA_INTEGRATION_ID]), body, format="json")

    def test_attach_and_detach(self):
        profile = self.create_profile()
        response = self.put_integration(profile["id"])
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(str(response.data["mapping_profile"]), profile["id"])

        response = self.put_integration(None)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["mapping_profile"])

    def test_profile_of_another_integrator(self):
        profile = self.create_profile(profile_body(code="test", integrator="Test"))
        response = self.put_integration(profile["id"])
        self.assertEqual(response.status_code, 400)
        self.assertIn("mapping_profile", response.data)

    def test_integrator_change_checks_kept_profile(self):
        self.attach_profile(self.create_profile()["id"])
        body = {"integrator": "Test", "tenant": TENANT_ID, "hotel_id": "999"}  # mapping_profile left out
        response = self.put(reverse("services:integration-detail", args=[HOTEZA_INTEGRATION_ID]), body, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("mapping_profile", response.data)


class MappingOverrideAPITest(MappingTestCase):
    def setUp(self):
        super().setUp()
        self.profile = self.create_profile()
        self.attach_profile(self.profile["id"])

    def create_override(self, **body):
        body = {"integration": HOTEZA_INTEGRATION_ID, "level": "tenant", "rule_overrides": {}, **body}
        return self.post(reverse("services:mapping-override-list"), body, format="json")

    def test_levels(self):
        reject = {"dimmer": {"on_invalid": "reject"}}
        for level, target in (("tenant", {}), ("room_type", {"room_type": ROOM_TYPE_ID}), ("room", {"room": ROOM_ID})):
            with self.subTest(level=level):
                response = self.create_override(level=level, rule_overrides=reject, **target)
                self.assertEqual(response.status_code, 201, response.data)
        response = self.create_override(level="device", device=DEVICE_ID, rule_overrides=reject)
        self.assertEqual(response.status_code, 201, response.data)

        response = self.get(reverse("services:mapping-override-list"), {"level": "device"})
        assert response.data is not None
        self.assertEqual([str(row["device"]) for row in response.data["results"]], [DEVICE_ID])

    def test_target_must_match_level(self):
        response = self.create_override(level="room")
        self.assertEqual(response.status_code, 400)
        self.assertIn("room", response.data)

        response = self.create_override(level="tenant", room=ROOM_ID)
        self.assertEqual(response.status_code, 400)
        self.assertIn("room", response.data)

    def test_one_override_per_target(self):
        self.assertEqual(self.create_override().status_code, 201)
        self.assertEqual(self.create_override().status_code, 400)

    def test_rule_overrides_are_validated(self):
        response = self.create_override(rule_overrides={"nope": {"on_invalid": "reject"}})
        self.assertEqual(response.status_code, 400)
        self.assertIn("not in the integration", str(response.data))

        response = self.create_override(rule_overrides={"dimmer": {"tag_type": "FCUSPEED"}})
        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot change", str(response.data))

        # The merged rule is checked like a profile rule: a 0-255 GRMS range does not fit "0-100".
        wide = {"transform": {**DIMMER["transform"], "grms": {"min": 0, "max": 255}}}
        response = self.create_override(rule_overrides={"dimmer": wide})
        self.assertEqual(response.status_code, 400)
        self.assertIn("0-255", str(response.data))

    def test_integration_without_profile(self):
        self.attach_profile(None)
        response = self.create_override()
        self.assertEqual(response.status_code, 400)
        self.assertIn("integration", response.data)

    def test_profile_update_keeps_overrides_valid(self):
        self.assertEqual(self.create_override(rule_overrides={"dimmer": {"on_invalid": "reject"}}).status_code, 201)
        url = reverse("services:mapping-profile-detail", args=[self.profile["id"]])
        response = self.put(url, profile_body(FAN_SPEED), format="json")  # drops the dimmer rule
        self.assertEqual(response.status_code, 400)
        self.assertIn("dimmer", str(response.data))

    def test_update_and_delete(self):
        override = self.create_override().data
        url = reverse("services:mapping-override-detail", args=[override["id"]])
        body = {"integration": HOTEZA_INTEGRATION_ID, "level": "tenant", "rule_overrides": {"dimmer": {}}}
        response = self.put(url, body, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["rule_overrides"], {"dimmer": {}})

        self.assertEqual(self.delete(url).status_code, 204)
        self.assertFalse(MappingOverride.objects.exists())

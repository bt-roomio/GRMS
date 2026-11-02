from django.urls import reverse

from core.tests.base import BaseTestCase
from services.models import Integration, MappingProfile

TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"  # admin@gmail.com's tenant
OTHER_TENANT_ID = "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc"
HOTEZA_INTEGRATION_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
ROOM_TYPE_ID = "deb5db89-b9cf-4aee-989d-4a7a7bdeb096"
ROOM_ID = "df77f910-2dcd-45cf-b6be-054c744561a7"
DEVICE_ID = "47aef21b-6cc9-4ec5-8573-1a6f491940c0"

FAN_SPEED = {
    "tag_name": "fanSpeed",
    "external": {"value_type": "integer"},
    "transform": {
        "type": "enum",
        "map": [{"grms": "Low", "external": 1}, {"grms": "Medium", "external": 2}, {"grms": "High", "external": 3}],
    },
}
DIMMER = {
    "tag_name": "dimmer",
    "external": {"value_type": "integer"},
    "transform": {"type": "range", "grms": {"min": 0, "max": 100}, "external": {"min": 0, "max": 100, "step": 10}},
    "on_invalid": "clamp",
}


def enum_transform(*pairs):
    return {"type": "enum", "map": [{"grms": grms, "external": external} for grms, external in pairs]}


def profile_body(*rules, name="Hoteza", integrator="hoteza", **scope):
    """A profile body; ``scope`` adds scope, room_type or device."""
    rules = list(rules or (FAN_SPEED, DIMMER))
    return {"name": name, "integrator": integrator, "rules": rules, **scope}


def fan_speed_with_medium(external):
    """FAN_SPEED with "Medium" sent as ``external``."""
    return {**FAN_SPEED, "transform": enum_transform(("Low", 1), ("Medium", external), ("High", 3))}


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

    def create_profile(self, body=None):
        response = self.post(reverse("services:mapping-profile-list"), body or profile_body(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def attach_profile(self, profile_id):
        Integration.objects.filter(pk=HOTEZA_INTEGRATION_ID).update(mapping_profile_id=profile_id)


class MappingProfileAPITest(MappingTestCase):
    def test_create_and_list(self):
        profile = self.create_profile()
        rules = {rule["tag_name"]: rule for rule in profile["rules"]}
        self.assertEqual(set(rules), {"fanSpeed", "dimmer"})
        self.assertEqual(rules["fanSpeed"]["direction"], "both")
        self.assertEqual(rules["fanSpeed"]["on_invalid"], "reject")
        self.assertNotIn("id", rules["fanSpeed"])

        response = self.get(reverse("services:mapping-profile-list"))
        assert response.data is not None
        self.assertEqual([row["name"] for row in response.data["results"]], ["Hoteza"])

    def test_rule_structure_is_validated(self):
        broken = {**DIMMER, "transform": {**DIMMER["transform"], "external": {"min": 0, "max": 100, "step": 0}}}
        response = self.post(reverse("services:mapping-profile-list"), profile_body(broken), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("step", str(response.data))

    def test_one_rule_per_tag_name(self):
        twin = {**FAN_SPEED, "direction": "to_external"}
        response = self.post(reverse("services:mapping-profile-list"), profile_body(FAN_SPEED, twin), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Duplicate tag names", str(response.data))

    def test_tags_of_one_kind_get_their_own_rules(self):
        # Two dimmers of one device with different GRMS scales: one rule per tag name.
        dimmer_255 = {
            **DIMMER,
            "tag_name": "dimmer_2",
            "transform": {**DIMMER["transform"], "grms": {"min": 0, "max": 255}},
        }
        profile = self.create_profile(profile_body(DIMMER, dimmer_255))
        rules = {rule["tag_name"]: rule["transform"]["grms"] for rule in profile["rules"]}
        self.assertEqual(rules, {"dimmer": {"min": 0, "max": 100}, "dimmer_2": {"min": 0, "max": 255}})

    def test_tag_name_is_required(self):
        response = self.post(
            reverse("services:mapping-profile-list"), profile_body({**FAN_SPEED, "tag_name": ""}), format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("tag_name", str(response.data))

    def test_name_is_unique_per_tenant(self):
        self.create_profile()
        response = self.post(reverse("services:mapping-profile-list"), profile_body(), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data)

    def test_update_replaces_rules(self):
        profile = self.create_profile()
        url = reverse("services:mapping-profile-detail", args=[profile["id"]])
        response = self.put(url, profile_body(DIMMER), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([rule["tag_name"] for rule in response.data["rules"]], ["dimmer"])

    def test_profile_of_another_tenant_is_hidden(self):
        profile = MappingProfile.objects.create(name="x", integrator_id="Test", tenant_id=OTHER_TENANT_ID)
        response = self.get(reverse("services:mapping-profile-detail", args=[profile.pk]))
        self.assertEqual(response.status_code, 404)

    def test_delete_detaches_integrations(self):
        profile = self.create_profile()
        self.attach_profile(profile["id"])
        response = self.delete(reverse("services:mapping-profile-detail", args=[profile["id"]]))
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(Integration.objects.get(pk=HOTEZA_INTEGRATION_ID).mapping_profile_id)


class ProfileAutoAttachTest(MappingTestCase):
    """A new tenant profile is attached to the integration of its integrator when that has none."""

    def integration_profile_id(self):
        profile_id = Integration.objects.get(pk=HOTEZA_INTEGRATION_ID).mapping_profile_id
        return str(profile_id) if profile_id else None

    def test_first_profile_is_attached(self):
        profile = self.create_profile()
        self.assertEqual(self.integration_profile_id(), profile["id"])
        self.assertEqual([str(pk) for pk in profile["integrations"]], [HOTEZA_INTEGRATION_ID])

    def test_attached_profile_is_not_replaced(self):
        first = self.create_profile()
        second = self.create_profile(profile_body(name="Hoteza v2"))
        self.assertEqual(self.integration_profile_id(), first["id"])
        self.assertEqual(second["integrations"], [])

    def test_scoped_profile_is_not_attached(self):
        self.create_profile(profile_body(name="room-101", scope="device", device=DEVICE_ID))
        self.assertIsNone(self.integration_profile_id())

    def test_profile_of_another_integrator_is_not_attached(self):
        self.create_profile(profile_body(name="test", integrator="Test"))
        self.assertIsNone(self.integration_profile_id())

    def test_inactive_integration_is_not_attached(self):
        Integration.objects.filter(pk=HOTEZA_INTEGRATION_ID).update(is_active=False)
        self.create_profile()
        self.assertIsNone(self.integration_profile_id())


class ScopedMappingProfileAPITest(MappingTestCase):
    def post_profile(self, body):
        return self.post(reverse("services:mapping-profile-list"), body, format="json")

    def test_create_room_type_and_device_profiles(self):
        room_type = self.create_profile(
            profile_body(FAN_SPEED, name="suite", scope="room_type", room_type=ROOM_TYPE_ID)
        )
        self.assertEqual(
            (room_type["scope"], str(room_type["room_type"]), room_type["device"]), ("room_type", ROOM_TYPE_ID, None)
        )
        device = self.create_profile(profile_body(DIMMER, name="room-101", scope="device", device=DEVICE_ID))
        self.assertEqual(str(device["device"]), DEVICE_ID)

        response = self.get(reverse("services:mapping-profile-list"), {"scope": "device"})
        assert response.data is not None
        self.assertEqual([row["name"] for row in response.data["results"]], ["room-101"])

    def test_target_must_match_scope(self):
        cases = (
            ({"scope": "room_type"}, "room_type"),
            ({"scope": "device", "room_type": ROOM_TYPE_ID, "device": DEVICE_ID}, "room_type"),
            ({"scope": "tenant", "device": DEVICE_ID}, "device"),
        )
        for scope, field in cases:
            with self.subTest(scope=scope):
                response = self.post_profile(profile_body(name="x", **scope))
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)

    def test_one_profile_per_target_and_integrator(self):
        body = profile_body(name="room-101", scope="device", device=DEVICE_ID)
        self.create_profile(body)
        response = self.post_profile({**body, "name": "room-101-bis"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("device", response.data)
        # Another integrator has its own profiles for the same device.
        self.create_profile({**body, "name": "test-101", "integrator": "Test"})

    def test_attached_profile_stays_tenant(self):
        profile = self.create_profile()
        self.attach_profile(profile["id"])
        url = reverse("services:mapping-profile-detail", args=[profile["id"]])
        response = self.put(url, profile_body(scope="device", device=DEVICE_ID), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("scope", response.data)

    def test_put_keeps_scope_when_left_out(self):
        profile = self.create_profile(profile_body(name="room-101", scope="device", device=DEVICE_ID))
        url = reverse("services:mapping-profile-detail", args=[profile["id"]])
        response = self.put(url, profile_body(DIMMER, name="room-101"), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual((response.data["scope"], str(response.data["device"])), ("device", DEVICE_ID))


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
        profile = self.create_profile(profile_body(name="test", integrator="Test"))
        response = self.put_integration(profile["id"])
        self.assertEqual(response.status_code, 400)
        self.assertIn("mapping_profile", response.data)

    def test_scoped_profile_cannot_be_attached(self):
        profile = self.create_profile(profile_body(name="room-101", scope="device", device=DEVICE_ID))
        response = self.put_integration(profile["id"])
        self.assertEqual(response.status_code, 400)
        self.assertIn("mapping_profile", response.data)

    def test_integrator_change_checks_kept_profile(self):
        self.attach_profile(self.create_profile()["id"])
        body = {"integrator": "Test", "tenant": TENANT_ID, "hotel_id": "999"}  # mapping_profile left out
        response = self.put(reverse("services:integration-detail", args=[HOTEZA_INTEGRATION_ID]), body, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("mapping_profile", response.data)

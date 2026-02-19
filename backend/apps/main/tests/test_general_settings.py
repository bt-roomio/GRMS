from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Tenant


class GeneralSettingsTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.url = reverse("main:general-settings-detail")
        self.tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"

    # ── GET ──────────────────────────────────────────────────────────────
    def test_get_success(self):
        """GET returns general settings with default fixture values."""
        response = self.get(self.url)
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["tenant_id"]), self.tenant_id)
        self.assertEqual(response.data["lang"], "en")
        self.assertEqual(response.data["timezone"], 0)
        self.assertEqual(response.data["controllers_sync"], False)
        self.assertEqual(response.data["check_in_out"], False)
        self.assertEqual(response.data["vip_status"], False)

    def test_get_returns_all_expected_fields(self):
        """GET response contains every field defined in the serializer."""
        response = self.get(self.url)
        self.assertEqual(response.status_code, 200)
        expected_fields = [
            "tenant_id",
            "lang",
            "roomio_node_url",
            "timezone",
            "controllers_sync",
            "check_in_out",
            "vip_status",
            "suite_rooms_controls_sync",
            "laundry",
            "visionline",
            "opera_integration",
            "visionline_card_system",
            "aperio_locks",
            "door_lock",
            "auto_checkout",
            "aggregate_db",
            "main_dashboard",
            "room_fields",
            "config",
        ]
        for field in expected_fields:
            self.assertIn(field, response.data, f"Missing field: {field}")

    def test_get_door_lock_defaults(self):
        """GET returns door_lock with default ving_card=False and kaba=False."""
        response = self.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["door_lock"], {"ving_card": False, "kaba": False})

    def test_get_room_fields_defaults(self):
        """GET returns room_fields as empty list by default."""
        response = self.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["room_fields"], [])

    # ── PUT – basic update ───────────────────────────────────────────────
    def test_put_update_lang(self):
        """PUT updates the lang setting."""
        payload = {"lang": "ru"}
        response = self.put(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["lang"], "ru")
        # tenant_id stays the same
        self.assertEqual(str(response.data["tenant_id"]), self.tenant_id)

    def test_put_update_boolean_fields(self):
        """PUT toggles boolean fields."""
        payload = {
            "controllers_sync": True,
            "check_in_out": True,
            "vip_status": True,
            "laundry": True,
        }
        response = self.put(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        for key, val in payload.items():
            self.assertEqual(response.data[key], val, f"Mismatch for {key}")

    def test_put_update_timezone(self):
        """PUT updates timezone."""
        payload = {"timezone": 5}
        response = self.put(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["timezone"], 5)

    def test_put_update_door_lock(self):
        """PUT updates nested door_lock object."""
        payload = {"door_lock": {"ving_card": True, "kaba": False}}
        response = self.put(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["door_lock"], {"ving_card": True, "kaba": False})

    def test_put_update_config(self):
        """PUT updates config JSON field."""
        payload = {"config": {"custom_key": "custom_value", "nested": {"a": 1}}}
        response = self.put(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["config"]["custom_key"], "custom_value")

    def test_put_persists_to_db(self):
        """PUT changes are persisted in the Tenant model's additional_info."""
        payload = {"lang": "fr", "timezone": 3}
        self.put(self.url, data=payload, format="json")

        tenant = Tenant.objects.get(id=self.tenant_id)
        g_settings = tenant.additional_info["general_settings"]
        self.assertEqual(g_settings["lang"], "fr")
        self.assertEqual(g_settings["timezone"], 3)

    def test_put_room_fields_telemetry_tag(self):
        """PUT accepts a telemetry room_field tag."""
        payload = {
            "room_fields": [
                {"name": "temperature", "tag_type": "telemetry"},
            ]
        }
        response = self.put(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["room_fields"]), 1)
        self.assertEqual(response.data["room_fields"][0]["name"], "temperature")

    def test_put_room_fields_attribute_requires_scope(self):
        """PUT with tag_type 'attribute' but no attribute_scope returns 400."""
        payload = {
            "room_fields": [
                {"name": "sensor", "tag_type": "attribute"},
            ]
        }
        response = self.put(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    # ── Permission / Auth ────────────────────────────────────────────────
    def test_get_unauthenticated_rejected(self):
        """Unauthenticated request is rejected."""
        self.client.credentials()
        response = self.get(self.url)
        self.assertIn(response.status_code, (401, 403))

    def test_put_unauthenticated_rejected(self):
        """Unauthenticated PUT is rejected."""
        self.client.credentials()
        response = self.put(self.url, data={"lang": "en"}, format="json")
        self.assertIn(response.status_code, (401, 403))

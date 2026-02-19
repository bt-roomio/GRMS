from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import AdminSettings


class AdminSettingsTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
    )

    def setUp(self):
        # admin@gmail.com is the only superuser in fixtures
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)
        self.tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"

        # Seed an AdminSettings record for GET / update tests
        self.existing_setting = AdminSettings.objects.create(
            key="hoteza",
            json_value={"hoteza_whitelist": ["192.168.1.1"]},
            tenant_id=self.tenant_id,
        )

    # ── helpers ──────────────────────────────────────────────────────────
    def _url(self, key="hoteza"):
        return reverse("main:admin-settings", kwargs={"key": key})

    # ── GET ──────────────────────────────────────────────────────────────
    def test_get_existing_setting(self):
        """GET returns the setting for a known key."""
        response = self.get(self._url("hoteza"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["key"], "hoteza")
        self.assertEqual(response.data["json_value"]["hoteza_whitelist"], ["192.168.1.1"])

    def test_get_non_existent_key(self):
        """GET for a key that doesn't exist returns 200 with null fields."""
        response = self.get(self._url("non_existent_key"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["key"], "")

    # ── PUT – create / update ────────────────────────────────────────────
    def test_put_update_existing_setting(self):
        """PUT updates an existing setting's json_value."""
        payload = {
            "json_value": {"hoteza_whitelist": ["10.0.0.1", "10.0.0.2"]},
        }
        response = self.put(self._url("hoteza"), data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["json_value"]["hoteza_whitelist"],
            ["10.0.0.1", "10.0.0.2"],
        )

        # Verify DB was updated
        self.existing_setting.refresh_from_db()
        self.assertEqual(
            self.existing_setting.json_value["hoteza_whitelist"],
            ["10.0.0.1", "10.0.0.2"],
        )

    def test_put_create_new_setting(self):
        """PUT for a new key creates the AdminSettings record."""
        payload = {
            "json_value": {"hoteza_whitelist": ["172.16.0.1"]},
        }
        response = self.put(self._url("new_key"), data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["key"], "new_key")
        self.assertTrue(AdminSettings.objects.filter(key="new_key").exists())

    def test_put_replaces_whitelist(self):
        """PUT completely replaces the previous whitelist."""
        payload = {
            "json_value": {"hoteza_whitelist": ["1.1.1.1"]},
        }
        self.put(self._url("hoteza"), data=payload, format="json")

        self.existing_setting.refresh_from_db()
        self.assertEqual(
            self.existing_setting.json_value["hoteza_whitelist"],
            ["1.1.1.1"],
        )

    def test_put_empty_whitelist(self):
        """PUT with an empty hoteza_whitelist returns 400 (allow_empty=False)."""
        payload = {
            "json_value": {"hoteza_whitelist": []},
        }
        response = self.put(self._url("hoteza"), data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_put_missing_whitelist_key(self):
        """PUT with json_value missing the required hoteza_whitelist field returns 400."""
        payload = {
            "json_value": {"some_other_field": "value"},
        }
        response = self.put(self._url("hoteza"), data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    # ── Permission / Auth ────────────────────────────────────────────────
    def test_non_superuser_get_rejected(self):
        """Non-superuser receives 403 on GET."""
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        response = self.get(self._url("hoteza"))
        self.assertEqual(response.status_code, 403)

    def test_non_superuser_put_rejected(self):
        """Non-superuser receives 403 on PUT."""
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        payload = {
            "json_value": {"hoteza_whitelist": ["10.0.0.1"]},
        }
        response = self.put(self._url("hoteza"), data=payload, format="json")
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_get_rejected(self):
        """Unauthenticated request is rejected."""
        self.client.credentials()
        response = self.get(self._url("hoteza"))
        self.assertIn(response.status_code, (401, 403))

    def test_unauthenticated_put_rejected(self):
        """Unauthenticated PUT request is rejected."""
        self.client.credentials()
        payload = {
            "json_value": {"hoteza_whitelist": ["10.0.0.1"]},
        }
        response = self.put(self._url("hoteza"), data=payload, format="json")
        self.assertIn(response.status_code, (401, 403))

    # ── Response structure ───────────────────────────────────────────────
    def test_get_response_contains_expected_fields(self):
        """GET response includes id, key, json_value, and tenant."""
        response = self.get(self._url("hoteza"))
        self.assertEqual(response.status_code, 200)
        for field in ("id", "key", "json_value", "tenant"):
            self.assertIn(field, response.data)

    def test_put_injects_tenant_from_user(self):
        """PUT automatically sets the tenant from the request user, not the payload."""
        payload = {
            "json_value": {"hoteza_whitelist": ["8.8.8.8"]},
            "tenant": "00000000-0000-0000-0000-000000000000",  # bogus tenant
        }
        response = self.put(self._url("hoteza"), data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        # tenant should be user's tenant, not the one in the payload
        self.assertEqual(str(response.data["tenant"]), self.tenant_id)

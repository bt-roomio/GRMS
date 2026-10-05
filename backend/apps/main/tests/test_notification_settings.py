from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Tenant

TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"


class NotificationSettingsTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.url = reverse("main:notification-settings")

    def test_get_returns_the_defaults_for_an_unconfigured_tenant(self):
        response = self.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["tenant_id"]), TENANT_ID)
        self.assertFalse(response.data["telegram_enabled"])
        self.assertEqual(response.data["telegram_chat_id"], "")
        self.assertEqual(response.data["notify_delay_sec"], 300)
        self.assertEqual(response.data["min_severity"], "MINOR")

    def test_put_stores_the_settings(self):
        response = self.put(
            self.url,
            data={"telegram_enabled": True, "telegram_chat_id": "-100500", "min_severity": "MAJOR"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["telegram_enabled"])
        self.assertEqual(response.data["telegram_chat_id"], "-100500")
        self.assertEqual(response.data["min_severity"], "MAJOR")

    def test_other_settings_blocks_are_left_alone(self):
        self.put(self.url, data={"telegram_chat_id": "-100500"}, format="json")

        tenant = Tenant.objects.get(pk=TENANT_ID)
        self.assertIn("general_settings", tenant.additional_info)
        self.assertIn("integration_settings", tenant.additional_info)

    def test_changing_the_chat_clears_the_last_error(self):
        tenant = Tenant.objects.get(pk=TENANT_ID)
        info = tenant.additional_info or {}
        info["notification_settings"] = {"telegram_chat_id": "-1", "telegram_last_error": "chat not found"}
        Tenant.objects.filter(pk=TENANT_ID).update(additional_info=info)

        response = self.put(self.url, data={"telegram_chat_id": "-100500"}, format="json")
        self.assertIsNone(response.data["telegram_last_error"])

    def test_the_last_error_is_read_only(self):
        response = self.put(self.url, data={"telegram_last_error": "spoofed"}, format="json")
        self.assertIsNone(response.data["telegram_last_error"])

    def test_an_invalid_severity_is_rejected(self):
        response = self.put(self.url, data={"min_severity": "URGENT"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_authentication_is_required(self):
        self.client.credentials()
        self.assertEqual(self.get(self.url).status_code, 401)

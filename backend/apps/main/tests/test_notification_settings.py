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
        self.assertEqual(response.data["notify_delay_sec"], 300)
        self.assertEqual(response.data["min_severity"], "MINOR")
        self.assertEqual(
            response.data["channels"],
            {
                "telegram": {"enabled": False, "chat_id": "", "last_error": None},
                "email": {"enabled": False, "recipients": [], "last_error": None},
            },
        )

    def test_put_stores_the_settings(self):
        response = self.put(
            self.url,
            data={"min_severity": "MAJOR", "channels": {"telegram": {"enabled": True, "chat_id": "-100500"}}},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["min_severity"], "MAJOR")
        self.assertEqual(response.data["channels"]["telegram"]["chat_id"], "-100500")
        self.assertTrue(response.data["channels"]["telegram"]["enabled"])

    def test_a_put_to_one_channel_leaves_the_other_alone(self):
        self.put(self.url, data={"channels": {"telegram": {"enabled": True, "chat_id": "-100500"}}}, format="json")
        response = self.put(
            self.url, data={"channels": {"email": {"enabled": True, "recipients": ["ops@hotel.uz"]}}}, format="json"
        )

        self.assertEqual(response.data["channels"]["telegram"]["chat_id"], "-100500")
        self.assertTrue(response.data["channels"]["telegram"]["enabled"])
        self.assertEqual(response.data["channels"]["email"]["recipients"], ["ops@hotel.uz"])

        # A partial channel block merges, it does not replace.
        response = self.put(self.url, data={"channels": {"telegram": {"enabled": False}}}, format="json")
        self.assertEqual(response.data["channels"]["telegram"]["chat_id"], "-100500")

    def test_other_settings_blocks_are_left_alone(self):
        self.put(self.url, data={"channels": {"telegram": {"chat_id": "-100500"}}}, format="json")

        tenant = Tenant.objects.get(pk=TENANT_ID)
        self.assertIn("general_settings", tenant.additional_info)
        self.assertIn("integration_settings", tenant.additional_info)

    def test_editing_a_channel_clears_only_its_last_error(self):
        tenant = Tenant.objects.get(pk=TENANT_ID)
        info = tenant.additional_info or {}
        info["notification_settings"] = {
            "channels": {
                "telegram": {"chat_id": "-1", "last_error": "chat not found"},
                "email": {"recipients": ["old@hotel.uz"], "last_error": "refused"},
            }
        }
        Tenant.objects.filter(pk=TENANT_ID).update(additional_info=info)

        response = self.put(self.url, data={"channels": {"telegram": {"chat_id": "-100500"}}}, format="json")
        self.assertIsNone(response.data["channels"]["telegram"]["last_error"])
        self.assertEqual(response.data["channels"]["email"]["last_error"], "refused")

    def test_the_last_error_is_read_only(self):
        response = self.put(self.url, data={"channels": {"telegram": {"last_error": "spoofed"}}}, format="json")
        self.assertIsNone(response.data["channels"]["telegram"]["last_error"])

    def test_email_recipients_are_validated_and_deduplicated(self):
        response = self.put(
            self.url,
            data={"channels": {"email": {"recipients": ["Ops@hotel.uz", "ops@hotel.uz", "eng@hotel.uz"]}}},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["channels"]["email"]["recipients"], ["ops@hotel.uz", "eng@hotel.uz"])

        response = self.put(self.url, data={"channels": {"email": {"recipients": ["not-an-email"]}}}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_an_invalid_severity_is_rejected(self):
        response = self.put(self.url, data={"min_severity": "URGENT"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_authentication_is_required(self):
        self.client.credentials()
        self.assertEqual(self.get(self.url).status_code, 401)

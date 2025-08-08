from django.urls import reverse

from core.tests.base import BaseTestCase


class ResetPasswordTests(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml", "reset_password.yaml")

    def test_reset_password(self):
        response = self.put(
            reverse("users:reset-password"),
            {
                "key": "7a8dd336c393cf37b68f9351711bea0db48657c4",
                "new_password": "Qwerty12345",
                "confirm_password": "Qwerty12345",
            },
        )
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("message"), "Password updated.")

    def test_invalid_email_reset(self):
        response = self.put(
            reverse("users:reset-password"),
            {"key": "invalid_key", "new_password": "Qwerty12345", "confirm_password": "Qwerty12345"},
        )
        assert response.data is not None
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["key"][0], "Invalid reset password token.")

from django.urls import reverse

from core.tests.base_test import BaseTestCase


class SendLinkTests(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "email_configuration.yaml",
    )

    def test_activation_link(self):
        # Case
        response = self.post(reverse("users:send-link"), data={"email": "admin@gmail.com"}, format="json")
        assert response is not None
        self.assertEqual(response.status_code, 200)

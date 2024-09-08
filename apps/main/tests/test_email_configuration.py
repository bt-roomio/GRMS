from django.urls import reverse
from core.tests.base_test import BaseTestCase


class EmailConfigurationTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "groups_permissions.yaml",
        "users.yaml",
        "email_configuration.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def test_list(self):
        response = self.client.get(reverse("main:email-config-detail"))
        self.assertEqual(response.data["host"], "smtp-mail.outlook.com")
        self.assertEqual(response.data["port"], "587")
        self.assertEqual(response.data["email"], "admin@room.io")
        self.assertEqual(response.data["password"], "Admin12345")
        self.assertEqual(response.data["username"], "Admin")

    def test_update(self):
        data = {
            "email": "test@gmail.com",
            "host": "host-smtp.gmail.com",
            "username": "amigo@gmail.com",
            "password": "Amigo12345",
            "port": "587",
        }
        response = self.client.put(reverse("main:email-config-detail"), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["host"], "host-smtp.gmail.com")
        self.assertEqual(response.data["email"], "test@gmail.com")
        self.assertEqual(response.data["username"], "amigo@gmail.com")
        self.assertEqual(response.data["password"], "Amigo12345")
        self.assertEqual(response.data["port"], "587")

        response = self.client.put(reverse("main:email-config-detail"), {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["host"], ["This field is required."])
        self.assertEqual(response.data["email"], ["This field is required."])
        self.assertEqual(response.data["username"], ["This field is required."])
        self.assertEqual(response.data["password"], ["This field is required."])
        self.assertEqual(response.data["port"], ["This field is required."])

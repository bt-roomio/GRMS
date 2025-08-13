from django.urls import reverse

from core.tests.base import BaseTestCase


class EmailConfigurationTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "email_configuration.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)

    def test_get_success(self):
        response = self.get(reverse("main:email-config-detail"))
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["host"], "smtp-mail.outlook.com")
        self.assertEqual(response.data["port"], "587")
        self.assertEqual(response.data["email"], "admin@room.io")
        self.assertEqual(response.data["password"], "Admin12345")
        self.assertEqual(response.data["username"], "Admin")

    def test_get_no_configuration(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.angelina_token)
        response = self.get(reverse("main:email-config-detail"))
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["host"], "")
        self.assertEqual(response.data["email"], "")
        self.assertEqual(response.data["tenant"], None)
        self.assertEqual(response.data["username"], "")
        self.assertEqual(response.data["password"], "")
        self.assertEqual(response.data["port"], "")
        self.assertEqual(response.data["use_tls"], False)
        self.assertEqual(response.data["frontend_host"], "")
        self.assertEqual(response.data["frontend_port"], "")

    def test_update_success(self):
        data = {
            "email": "test@gmail.com",
            "host": "host-smtp.gmail.com",
            "username": "amigo@gmail.com",
            "password": "Amigo12345",
            "port": "587",
            "use_tls": True,
            "frontend_host": "localhost",
            "frontend_port": "3000",
        }
        response = self.put(reverse("main:email-config-detail"), data, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["host"], "host-smtp.gmail.com")
        self.assertEqual(response.data["email"], "test@gmail.com")
        self.assertEqual(response.data["username"], "amigo@gmail.com")
        self.assertEqual(response.data["password"], "Amigo12345")
        self.assertEqual(response.data["port"], "587")
        self.assertEqual(response.data["use_tls"], True)
        self.assertEqual(response.data["frontend_host"], "localhost")
        self.assertEqual(response.data["frontend_port"], "3000")

    def test_update_partial(self):
        data = {"email": "partial@gmail.com", "host": "new-host.gmail.com"}
        response = self.put(reverse("main:email-config-detail"), data, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "partial@gmail.com")
        self.assertEqual(response.data["host"], "new-host.gmail.com")

    def test_update_invalid_email(self):
        data = {
            "email": "invalid-email",
            "host": "smtp.gmail.com",
            "username": "test",
            "password": "test123",
            "port": "587",
        }
        response = self.put(reverse("main:email-config-detail"), data, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", "Enter a valid email")

    def test_create_new_configuration(self):
        data = {
            "email": "new@gmail.com",
            "host": "smtp.gmail.com",
            "username": "newuser",
            "password": "newpass123",
            "port": "587",
        }
        response = self.put(reverse("main:email-config-detail"), data, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "new@gmail.com")

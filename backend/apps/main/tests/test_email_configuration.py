from django.urls import reverse

from core.tests.base_test import BaseTestCase
from main.models import EmailConfiguration
from users.models import User


class EmailConfigurationTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "email_configuration.yaml",
    )

    def setUp(self):
        self.user = User.objects.get(pk='da16dcfd-b885-4966-84db-c3e26ff50afc')
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def test_get_success(self):
        response = self.client.get(reverse("main:email-config-detail"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["host"], "smtp-mail.outlook.com")
        self.assertEqual(response.data["port"], "587")
        self.assertEqual(response.data["email"], "admin@room.io")
        self.assertEqual(response.data["password"], "Admin12345")
        self.assertEqual(response.data["username"], "Admin")

    def test_get_no_configuration(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.first()
        EmailConfiguration.objects.filter(tenant=user.tenant).delete()

        response = self.client.get(reverse("main:email-config-detail"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["host"], "")
        self.assertEqual(response.data["email"], "")

    def test_update_success(self):
        data = {
            "email": "test@gmail.com",
            "host": "host-smtp.gmail.com",
            "username": "amigo@gmail.com",
            "password": "Amigo12345",
            "port": "587",
            "use_tls": True,
            "frontend_host": "localhost",
            "frontend_port": "3000"
        }
        response = self.client.put(reverse("main:email-config-detail"), data, format="json")
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
        data = {
            "email": "partial@gmail.com",
            "host": "new-host.gmail.com"
        }
        response = self.client.put(reverse("main:email-config-detail"), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "partial@gmail.com")
        self.assertEqual(response.data["host"], "new-host.gmail.com")

    def test_update_missing_fields_validation(self):
        response = self.client.put(reverse("main:email-config-detail"), {}, format="json")

        self.assertEqual(response.status_code, 200)


    def test_update_invalid_email(self):
        data = {
            "email": "invalid-email",
            "host": "smtp.gmail.com",
            "username": "test",
            "password": "test123",
            "port": "587"
        }
        response = self.client.put(reverse("main:email-config-detail"), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_create_new_configuration(self):
        EmailConfiguration.objects.filter(tenant=self.user.tenant).delete()

        data = {
            "email": "new@gmail.com",
            "host": "smtp.gmail.com",
            "username": "newuser",
            "password": "newpass123",
            "port": "587"
        }
        response = self.client.put(reverse("main:email-config-detail"), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "new@gmail.com")

        config = EmailConfiguration.objects.get(tenant=self.user.tenant)
        self.assertEqual(config.email, "new@gmail.com")


    def test_update_by_field_tracking(self):
        data = {
            "email": "updated@gmail.com",
            "host": "smtp.gmail.com",
            "username": "updated",
            "password": "updated123",
            "port": "587"
        }
        response = self.client.put(reverse("main:email-config-detail"), data, format="json")
        self.assertEqual(response.status_code, 200)

        config = EmailConfiguration.objects.get(tenant=self.user.tenant)
        self.assertEqual(config.updated_by, self.user)

    def test_boolean_field_handling(self):
        data = {
            "email": "test@gmail.com",
            "host": "smtp.gmail.com",
            "username": "test",
            "password": "test123",
            "port": "587",
            "use_tls": True
        }
        response = self.client.put(reverse("main:email-config-detail"), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["use_tls"])

        data["use_tls"] = False
        response = self.client.put(reverse("main:email-config-detail"), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["use_tls"])

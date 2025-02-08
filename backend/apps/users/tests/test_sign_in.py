from django.urls import reverse

from core.tests.base_test import BaseTestCase


class SignInTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def test_signin_success(self):
        response = self.client.get(reverse("users:users-detail", kwargs={"pk": "da16dcfd-b885-4966-84db-c3e26ff50afc"}))
        self.assertEqual(200, response.status_code, response.data)
        self.assertIn("id", response.data, response.data)
        self.assertIn("email", response.data, response.data)
        self.assertIn("additional_info", response.data, response.data)
        self.assertIn("first_name", response.data, response.data)
        self.assertIn("last_name", response.data, response.data)
        self.assertIn("tenant", response.data, response.data)

    def test_signin_fail(self):
        self.client.credentials()
        response = self.client.get(reverse("users:users-detail", kwargs={"pk": "a16345ba-639a-4be7-b9ac-86415dfe630a"}))
        self.assertEqual(401, response.status_code, response.data)

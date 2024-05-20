from django.urls import reverse
from core.tests.base_test import BaseTestCase


class SignInTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def test_signin_success(self):
        response = self.client.get(reverse("users:sign-in"))
        self.assertEqual(200, response.status_code, response.data)
        self.assertIn("id", response.data, response.data)
        self.assertIn("email", response.data, response.data)
        self.assertIn("created_at", response.data, response.data)

    def test_signin_fail(self):
        self.client.credentials()
        response = self.client.get(reverse("users:sign-in"))
        self.assertEqual(401, response.status_code, response.data)

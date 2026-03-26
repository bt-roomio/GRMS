from django.urls import reverse

from core.tests.base import BaseTestCase


class SimpleGroupViewTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)
        self.url = reverse("main:simple-group-list")

    def test_returns_200(self):
        response = self.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_response_is_list(self):
        response = self.get(self.url)
        self.assertIsInstance(response.data, list)

    def test_response_fields(self):
        response = self.get(self.url)
        for item in response.data:
            self.assertIn("id", item)
            self.assertIn("name", item)
            self.assertEqual(len(item), 2)

    def test_unauthorized(self):
        self.client.credentials()
        response = self.get(self.url)
        self.assertEqual(response.status_code, 401)

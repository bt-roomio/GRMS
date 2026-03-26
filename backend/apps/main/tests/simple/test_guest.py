from django.urls import reverse

from core.tests.base import BaseTestCase


class SimpleGuestViewTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml", "room.yaml", "guest.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.url = reverse("main:simple-guest-list")

    def test_returns_200(self):
        response = self.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_response_fields(self):
        response = self.get(self.url)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)
        item = response.data[0]
        self.assertIn("id", item)
        self.assertIn("name", item)
        self.assertIn("lastname", item)
        self.assertEqual(len(item), 3)

    def test_search_by_name(self):
        response = self.get(self.url, {"search_field": "name", "search_value": "Amigo"})
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Amigo")

    def test_search_by_lastname(self):
        response = self.get(self.url, {"search_field": "lastname", "search_value": "Slav"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["lastname"], "Slaven")

    def test_search_no_results(self):
        response = self.get(self.url, {"search_field": "name", "search_value": "nonexistent"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_unauthorized(self):
        self.client.credentials()
        response = self.get(self.url)
        self.assertEqual(response.status_code, 401)

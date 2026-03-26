from django.urls import reverse

from core.tests.base import BaseTestCase


class SimpleRoomViewTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml", "room.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.url = reverse("main:simple-room-list")

    def test_returns_200(self):
        response = self.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_response_fields(self):
        response = self.get(self.url)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)
        item = response.data[0]
        self.assertIn("id", item)
        self.assertIn("number", item)
        self.assertIn("floor", item)
        self.assertIn("block", item)
        self.assertEqual(len(item), 4)

    def test_unauthorized(self):
        self.client.credentials()
        response = self.get(self.url)
        self.assertEqual(response.status_code, 401)

from django.urls import reverse

from core.tests.base import BaseTestCase


class RolesTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.angelina_token)

    def test_list(self):
        response = self.get(reverse("users:roles-list"))
        self.assertEqual(response.status_code, 200)
        assert response.data is not None
        self.assertEqual(response.data[0]["name"], "Reception")
        self.assertEqual(response.data[0]["id"], "d3c94703-ab5e-4926-ac52-a9bf8cf34ac6")

    def test_create(self):
        response = self.post(reverse("users:roles-list"), data={"name": "NEW_ROLE", "permissions": []}, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "NEW_ROLE")
        self.assertEqual(response.data["permissions"], [])

    def test_update(self):
        response = self.put(
            reverse("users:roles-detail", kwargs={"pk": "d3c94703-ab5e-4926-ac52-a9bf8cf34ac6"}),
            data={"name": "UPDATED_ROLE"},
        )
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "UPDATED_ROLE")

    def test_get(self):
        response = self.get(reverse("users:roles-detail", kwargs={"pk": "d3c94703-ab5e-4926-ac52-a9bf8cf34ac6"}))
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Reception")

    def test_delete(self):
        response = self.delete(reverse("users:roles-detail", kwargs={"pk": "d3c94703-ab5e-4926-ac52-a9bf8cf34ac6"}))
        self.assertEqual(response.status_code, 204)

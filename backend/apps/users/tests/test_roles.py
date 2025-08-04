from typing import cast

from django.urls import reverse

from rest_framework.response import Response

from core.tests.base_test import BaseTestCase


class RolesTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.angelina_token)

    def test_list(self):
        response = cast(Response, self.client.get(reverse("users:roles-list")))
        self.assertEqual(response.status_code, 200)
        assert response.data is not None
        self.assertEqual(response.data[0]["name"], "TENANT_ADMIN")
        self.assertEqual(response.data[0]["id"], "bb436b2a-2ff5-4835-a264-fe27e30710e6")

    def test_create(self):
        response = cast(
            Response,
            self.client.post(reverse("users:roles-list"), data={"name": "NEW_ROLE", "permissions": []}, format="json"),
        )
        assert response.data is not None
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "NEW_ROLE")
        self.assertEqual(response.data["permissions"], [])

    def test_update(self):
        response = cast(
            Response,
            self.client.put(
                reverse("users:roles-detail", kwargs={"pk": "bb436b2a-2ff5-4835-a264-fe27e30710e6"}),
                data={"name": "UPDATED_ROLE"},
            ),
        )
        assert response.data is not None

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "UPDATED_ROLE")

    def test_get(self):
        response = cast(
            Response,
            self.client.get(reverse("users:roles-detail", kwargs={"pk": "bb436b2a-2ff5-4835-a264-fe27e30710e6"})),
        )
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "TENANT_ADMIN")

    def test_delete(self):
        response = cast(
            Response,
            self.client.delete(reverse("users:roles-detail", kwargs={"pk": "bb436b2a-2ff5-4835-a264-fe27e30710e6"})),
        )
        self.assertEqual(response.status_code, 204)

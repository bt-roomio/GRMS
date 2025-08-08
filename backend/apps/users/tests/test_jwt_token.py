from django.urls import reverse

from rest_framework import status

from core.tests.base import BaseTestCase


class CustomTokenViewsTests(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def test_jwt_token(self):
        # Case
        user_data = {"email": "angelina@gmail.com", "password": "password"}
        response = self.post(reverse("users:access-token"), user_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assert response.data is not None
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        # Case
        refresh_token = response.data["refresh"]
        response = self.post(reverse("users:refresh-token"), {"refresh": refresh_token})
        assert response.data is not None
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

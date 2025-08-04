from typing import cast

from django.urls import reverse

from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase


class CustomTokenViewsTests(APITestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def test_jwt_token(self):
        # Case
        user_data = {"email": "angelina@gmail.com", "password": "password"}
        response = cast(Response, self.client.post(reverse("users:access-token"), user_data))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assert response.data is not None
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        # Case
        refresh_token = response.data["refresh"]
        response = cast(Response, self.client.post(reverse("users:refresh-token"), {"refresh": refresh_token}))
        assert response.data is not None
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

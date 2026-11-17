from django.contrib.auth.models import Permission
from django.urls import reverse

from rest_framework import status

from core.tests.base import BaseTestCase
from core.utils.constants import UI_PERMISSIONS
from users.models import Role


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

    def test_login_grants_all_permissions_to_admin_role(self):
        role = Role.objects.get(id="c4d5e6f7-1a2b-4c3d-9e8f-0a1b2c3d4e5f")  # angelina's TENANT_ADMIN
        role.permissions.remove(*Permission.objects.filter(codename__endswith="globalsettingstemplate"))
        role.additional_info = {"ui_permissions": ["main"], "note": "kept"}
        role.save()
        self.assertLess(role.permissions.count(), Permission.objects.count())

        response = self.post(reverse("users:access-token"), {"email": "angelina@gmail.com", "password": "password"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(role.permissions.count(), Permission.objects.count())
        role.refresh_from_db()
        self.assertEqual(role.additional_info, {"ui_permissions": UI_PERMISSIONS, "note": "kept"})

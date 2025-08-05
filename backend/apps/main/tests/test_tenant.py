from django.urls import reverse
from core.tests.base import BaseTestCase


class TenantListViewTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def test_list_tenants_success(self):
        url = reverse("main:tenant-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(response.data, list))
        self.assertGreaterEqual(len(response.data), 1)

        tenant = response.data[0]
        self.assertIn("id", tenant)
        self.assertIn("title", tenant)
        self.assertIn("email", tenant)
        self.assertIn("created_at", tenant)

    def test_list_tenants_permission_denied(self):
        self.client.credentials()  # No auth
        url = reverse("main:tenant-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

from django.urls import reverse

from core.tests.base import BaseTestCase


TENANT_ID = "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc"
OTHER_TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"
RECEPTION_ROLE_ID = "d3c94703-ab5e-4926-ac52-a9bf8cf34ac6"  # Reception (tenant: ac73203f)
NON_EXISTENT_ID = "11111111-1111-1111-1111-111111111111"


class AdminTenantRolesTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def test_list(self):
        response = self.get(reverse("admin_panel:admin-tenant-roles", kwargs={"tenant_id": TENANT_ID}))
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], RECEPTION_ROLE_ID)
        self.assertEqual(response.data[0]["name"], "Reception")

    def test_list_other_tenant(self):
        # OTHER_TENANT_ID has 2 roles: SYS_ADMIN and TENANT_ADMIN
        response = self.get(reverse("admin_panel:admin-tenant-roles", kwargs={"tenant_id": OTHER_TENANT_ID}))
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        names = [r["name"] for r in response.data]
        self.assertIn("SYS_ADMIN", names)
        self.assertIn("TENANT_ADMIN", names)

    def test_list_tenant_not_found(self):
        response = self.get(reverse("admin_panel:admin-tenant-roles", kwargs={"tenant_id": NON_EXISTENT_ID}))
        self.assertEqual(response.status_code, 404)

    def test_list_forbidden_for_non_superuser(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.angelina_token)
        response = self.get(reverse("admin_panel:admin-tenant-roles", kwargs={"tenant_id": TENANT_ID}))
        self.assertEqual(response.status_code, 403)

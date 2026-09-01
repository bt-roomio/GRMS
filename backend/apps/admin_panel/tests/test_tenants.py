from django.urls import reverse

from core.tests.base import BaseTestCase

TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"
TENANT_2_ID = "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc"
TENANT_PROFILE_ID = "da16dcf1-b885-4966-84db-c3e26ff50aad"
NON_EXISTENT_ID = "11111111-1111-1111-1111-111111111111"


class AdminTenantListTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def test_list(self):
        response = self.get(reverse("admin_panel:admin-tenant-list"))
        self.assertEqual(response.status_code, 200)
        assert response.data is not None
        ids = [t["id"] for t in response.data["results"]]
        self.assertIn(TENANT_ID, ids)
        self.assertIn(TENANT_2_ID, ids)

    def test_list_forbidden_for_non_superuser(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.angelina_token)
        response = self.get(reverse("admin_panel:admin-tenant-list"))
        self.assertEqual(response.status_code, 403)

    def test_create(self):
        # Case - missing required fields
        response = self.post(reverse("admin_panel:admin-tenant-list"), {})
        self.assertEqual(response.status_code, 400)

        # Case - successful creation
        response = self.post(
            reverse("admin_panel:admin-tenant-list"),
            {"title": "New Hotel", "email": "newhotel@gmail.com", "password": "Password1234"},
            format="json",
        )
        assert response.data is not None
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["title"], "New Hotel")

    def test_create_duplicate_title(self):
        response = self.post(
            reverse("admin_panel:admin-tenant-list"),
            {"title": "Tenant", "email": "unique@gmail.com", "password": "Password1234"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_duplicate_email(self):
        response = self.post(
            reverse("admin_panel:admin-tenant-list"),
            {"title": "Brand New Hotel", "email": "admin@gmail.com", "password": "Password1234"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class AdminTenantDetailTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def test_detail(self):
        response = self.get(reverse("admin_panel:admin-tenant-detail", kwargs={"tenant_id": TENANT_ID}))
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], TENANT_ID)
        self.assertEqual(response.data["title"], "Tenant")

    def test_detail_not_found(self):
        response = self.get(reverse("admin_panel:admin-tenant-detail", kwargs={"tenant_id": NON_EXISTENT_ID}))
        self.assertEqual(response.status_code, 404)

    def test_detail_forbidden_for_non_superuser(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.angelina_token)
        response = self.get(reverse("admin_panel:admin-tenant-detail", kwargs={"tenant_id": TENANT_ID}))
        self.assertEqual(response.status_code, 403)

    def test_update(self):
        response = self.put(
            reverse("admin_panel:admin-tenant-detail", kwargs={"tenant_id": TENANT_2_ID}),
            {
                "title": "Updated Hotel",
                "email": "updated@hotel.com",
                "phone": "+998901234567",
                "address": "123 Main St",
                "city": "Tashkent",
                "country": "UZ",
                "tenant_profile": TENANT_PROFILE_ID,
            },
            format="json",
        )
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Updated Hotel")
        self.assertEqual(response.data["email"], "updated@hotel.com")
        self.assertEqual(response.data["city"], "Tashkent")

    def test_update_not_found(self):
        response = self.put(
            reverse("admin_panel:admin-tenant-detail", kwargs={"tenant_id": NON_EXISTENT_ID}),
            {"title": "Ghost"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_update_duplicate_title(self):
        response = self.put(
            reverse("admin_panel:admin-tenant-detail", kwargs={"tenant_id": TENANT_2_ID}),
            {"title": "Tenant", "tenant_profile": TENANT_PROFILE_ID},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

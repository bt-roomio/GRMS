from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Room, Tenant, TenantGroup
from main.services.tenant_provisioning import provision_tenant_group
from users.models import User

TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"
TENANT_2_ID = "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc"
NON_EXISTENT_ID = "11111111-1111-1111-1111-111111111111"


class AdminTenantGroupTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)
        self.group = TenantGroup.objects.create(title="Chain")

    def test_list(self):
        response = self.get(reverse("admin_panel:admin-group-list"))
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual([g["title"] for g in response.data["results"]], ["Chain"])
        self.assertEqual(response.data["results"][0]["tenants_count"], 0)

    def create_group(self, **overrides):
        payload = {"title": "Marriott", "email": "owner@marriott.uz", "password": "secret"} | overrides
        return self.post(reverse("admin_panel:admin-group-list"), data=payload, format="json")

    def test_create(self):
        response = self.create_group()
        assert response.data is not None
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["title"], "Marriott")
        self.assertNotIn("password", response.data)

    def test_create_provisions_a_chain_admin(self):
        response = self.create_group()
        assert response.data is not None

        admin = User.objects.get(email="owner@marriott.uz")
        self.assertEqual(str(admin.tenant_group_id), str(response.data["id"]))
        self.assertTrue(admin.is_superuser)
        self.assertIsNone(admin.tenant_id)
        self.assertTrue(admin.check_password("secret"))

    def test_create_requires_an_admin(self):
        response = self.post(reverse("admin_panel:admin-group-list"), data={"title": "Marriott"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(TenantGroup.objects.filter(title="Marriott").exists())

    def test_create_with_taken_email_is_rejected(self):
        response = self.create_group(email="admin@gmail.com")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(TenantGroup.objects.filter(title="Marriott").exists())

    def test_create_duplicate_title_is_rejected(self):
        response = self.create_group(title="chain")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="owner@marriott.uz").exists())

    def test_update(self):
        url = reverse("admin_panel:admin-group-detail", kwargs={"group_id": self.group.pk})
        response = self.put(url, data={"title": "Chain Renamed"}, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Chain Renamed")

    def test_detail_not_found(self):
        url = reverse("admin_panel:admin-group-detail", kwargs={"group_id": NON_EXISTENT_ID})
        self.assertEqual(self.get(url).status_code, 404)

    def test_attach_and_detach_through_tenant_update(self):
        url = reverse("admin_panel:admin-tenant-detail", kwargs={"tenant_id": TENANT_ID})

        response = self.put(url, data={"group": str(self.group.pk)}, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["group"]), str(self.group.pk))

        response = self.put(url, data={"group": None}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(Tenant.objects.get(pk=TENANT_ID).group_id)

    def test_chain_hotels_are_listed_by_filter(self):
        Tenant.objects.filter(pk=TENANT_ID).update(group=self.group)

        response = self.get(reverse("admin_panel:admin-tenant-list"), {"group": str(self.group.pk)})
        assert response.data is not None
        self.assertEqual([str(t["id"]) for t in response.data], [TENANT_ID])

    def test_unscoped_superuser_can_impersonate_a_chain_admin(self):
        """Chain admins have no tenant; a tenant-only filter would hide them entirely."""
        provision_tenant_group(title="Marriott", email="owner@marriott.uz", password="secret")
        admin = User.objects.get(email="owner@marriott.uz")

        url = reverse("admin_panel:admin-impersonate", kwargs={"user_id": admin.pk})
        self.assertEqual(self.post(url).status_code, 200)

    def test_deleting_a_chain_deactivates_its_admins(self):
        """SET_NULL alone would leave the admin a superuser with system-wide reach."""
        group = provision_tenant_group(title="Marriott", email="owner@marriott.uz", password="secret")

        url = reverse("admin_panel:admin-group-detail", kwargs={"group_id": group.pk})
        self.assertEqual(self.delete(url).status_code, 204)

        admin = User.objects.get(email="owner@marriott.uz")
        self.assertFalse(admin.is_active)
        self.assertIsNone(admin.tenant_group_id)

    def test_deleting_a_chain_keeps_its_hotels(self):
        Tenant.objects.filter(pk=TENANT_ID).update(group=self.group)
        rooms_before = Room.objects.filter(tenant_id=TENANT_ID).count()

        url = reverse("admin_panel:admin-group-detail", kwargs={"group_id": self.group.pk})
        self.assertEqual(self.delete(url).status_code, 204)

        tenant = Tenant.objects.get(pk=TENANT_ID)
        self.assertIsNone(tenant.group_id)
        self.assertEqual(Room.objects.filter(tenant_id=TENANT_ID).count(), rooms_before)

    def test_tenant_list_can_be_filtered_by_chain(self):
        Tenant.objects.filter(pk=TENANT_ID).update(group=self.group)

        response = self.get(reverse("admin_panel:admin-tenant-list"), {"group": str(self.group.pk)})
        assert response.data is not None
        self.assertEqual([str(t["id"]) for t in response.data], [TENANT_ID])
        self.assertEqual(response.data[0]["group_title"], "Chain")

    def test_forbidden_for_non_superuser(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.angelina_token)
        self.assertEqual(self.get(reverse("admin_panel:admin-group-list")).status_code, 403)

    def test_pinning_requires_a_superuser_target(self):
        karina = User.objects.get(email="karina@gmail.com")  # ordinary user
        url = reverse(
            "admin_panel:admin-tenant-user-detail",
            kwargs={"tenant_id": karina.tenant_id, "user_id": karina.pk},
        )
        response = self.put(
            url,
            data={"email": karina.email, "roles": [], "tenant_group": str(self.group.pk)},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_pinning_a_superuser_to_a_chain(self):
        karina = User.objects.get(email="karina@gmail.com")
        User.objects.filter(pk=karina.pk).update(is_superuser=True)
        url = reverse(
            "admin_panel:admin-tenant-user-detail",
            kwargs={"tenant_id": karina.tenant_id, "user_id": karina.pk},
        )

        response = self.put(
            url,
            data={"email": karina.email, "roles": [], "tenant_group": str(self.group.pk)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.get(pk=karina.pk).tenant_group_id, self.group.pk)

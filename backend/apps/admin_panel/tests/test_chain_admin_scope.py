from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Tenant, TenantGroup
from users.models import User
from users.serializers.jwt_token import build_tokens_for

TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"
TENANT_2_ID = "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc"


class ChainAdminScopeTest(BaseTestCase):
    """A superuser pinned to a chain may administer that chain and nothing else."""

    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.group = TenantGroup.objects.create(title="Chain")
        Tenant.objects.filter(pk=TENANT_ID).update(group=self.group)
        self.outsider = Tenant.objects.exclude(pk=TENANT_ID).first()

        self.chain_admin = User.objects.get(email="karina@gmail.com")
        self.chain_admin.is_superuser = True
        self.chain_admin.tenant_group = self.group
        self.chain_admin.save(update_fields=["is_superuser", "tenant_group"])

        tokens = build_tokens_for(User.objects.get(pk=self.chain_admin.pk))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    def test_tenant_list_shows_only_the_chain(self):
        response = self.get(reverse("admin_panel:admin-tenant-list"))
        assert response.data is not None
        self.assertEqual([str(t["id"]) for t in response.data], [TENANT_ID])

    def test_foreign_tenant_is_invisible(self):
        url = reverse("admin_panel:admin-tenant-detail", kwargs={"tenant_id": self.outsider.pk})
        self.assertEqual(self.get(url).status_code, 404)

    def test_foreign_tenant_users_are_unreachable(self):
        url = reverse("admin_panel:admin-tenant-users", kwargs={"tenant_id": self.outsider.pk})
        self.assertEqual(self.get(url).status_code, 404)

    def test_created_tenant_lands_in_the_chain(self):
        response = self.post(
            reverse("admin_panel:admin-tenant-list"),
            data={"title": "Astoria", "email": "gm@astoria.uz", "password": "secret"},
            format="json",
        )
        assert response.data is not None
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Tenant.objects.get(title="Astoria").group_id, self.group.pk)

    def test_cannot_place_a_tenant_in_another_chain(self):
        other = TenantGroup.objects.create(title="Other")
        self.post(
            reverse("admin_panel:admin-tenant-list"),
            data={"title": "Astoria", "email": "gm@astoria.uz", "password": "secret", "group": str(other.pk)},
            format="json",
        )
        self.assertEqual(Tenant.objects.get(title="Astoria").group_id, self.group.pk)

    def test_sees_only_its_own_chain(self):
        TenantGroup.objects.create(title="Other")
        response = self.get(reverse("admin_panel:admin-group-list"))
        assert response.data is not None
        self.assertEqual(response.data["count"], 1)
        self.assertEqual([g["title"] for g in response.data["results"]], ["Chain"])

    def test_cannot_create_another_chain(self):
        response = self.post(reverse("admin_panel:admin-group-list"), data={"title": "Marriott"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_cannot_delete_its_own_chain(self):
        url = reverse("admin_panel:admin-group-detail", kwargs={"group_id": self.group.pk})
        self.assertEqual(self.delete(url).status_code, 403)

    def test_cannot_pin_anyone_to_a_chain(self):
        target = User.objects.get(email="test@gmail.com")  # inside the chain, reachable
        url = reverse(
            "admin_panel:admin-tenant-user-detail",
            kwargs={"tenant_id": target.tenant_id, "user_id": target.pk},
        )
        response = self.put(
            url,
            data={"email": target.email, "roles": [], "tenant_group": str(self.group.pk)},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_cannot_impersonate_outside_the_chain(self):
        romeo = User.objects.get(email="romeo@gmail.com")  # tenant 2, outside the chain
        url = reverse("admin_panel:admin-impersonate", kwargs={"user_id": romeo.pk})
        self.assertEqual(self.post(url).status_code, 404)

    def test_cannot_reach_a_hotel_of_another_chain(self):
        url = reverse("admin_panel:admin-tenant-detail", kwargs={"tenant_id": TENANT_2_ID})
        response = self.put(url, data={"group": str(self.group.pk)}, format="json")

        self.assertEqual(response.status_code, 404)
        self.assertIsNone(Tenant.objects.get(pk=TENANT_2_ID).group_id)

    def test_cannot_move_its_own_hotel_out_of_the_chain(self):
        url = reverse("admin_panel:admin-tenant-detail", kwargs={"tenant_id": TENANT_ID})
        response = self.put(url, data={"group": None}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Tenant.objects.get(pk=TENANT_ID).group_id, self.group.pk)

"""
A chain admin is a superuser, so every `if user.is_superuser` shortcut is a way out
of the chain. These tests pin the tenant-facing endpoints — the admin panel is
covered separately in `admin_panel/tests/test_chain_admin_scope.py`.
"""

from django.urls import reverse

from rest_framework_simplejwt.tokens import RefreshToken

from core.tests.base import BaseTestCase
from main.models import Tenant, TenantGroup
from main.services.tenant_provisioning import provision_tenant_group
from users.models import Role, User
from users.utils.tenant_access import available_tenants_qs

TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"
TENANT_2_ID = "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc"


class ChainAdminIsolationTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.group = provision_tenant_group(title="Chain", email="chain@admin.uz", password="password")
        Tenant.objects.filter(pk=TENANT_ID).update(group=self.group)
        outsider = User.objects.filter(tenant_id=TENANT_2_ID, is_active=True).first()
        assert outsider is not None
        self.outsider = outsider
        self.client.credentials(HTTP_AUTHORIZATION=self.chain_token)

    @property
    def chain_token(self):
        refresh = RefreshToken.for_user(User.objects.get(email="chain@admin.uz"))
        return f"Bearer {refresh.access_token}"

    def test_cannot_read_a_user_outside_the_chain(self):
        url = reverse("users:users-detail", kwargs={"pk": self.outsider.pk})
        self.assertEqual(self.get(url).status_code, 404)

    def test_cannot_edit_a_user_outside_the_chain(self):
        url = reverse("users:users-detail", kwargs={"pk": self.outsider.pk})
        response = self.put(url, data={"email": "hacked@x.com", "roles": []}, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(User.objects.get(pk=self.outsider.pk).email, self.outsider.email)

    def test_can_read_a_user_inside_the_chain(self):
        insider = User.objects.filter(tenant_id=TENANT_ID, is_active=True).first()
        assert insider is not None
        url = reverse("users:users-detail", kwargs={"pk": insider.pk})
        self.assertEqual(self.get(url).status_code, 200)

    def test_cannot_touch_a_role_outside_the_chain(self):
        outside_role = Role.objects.filter(tenant_id=TENANT_2_ID).first()
        assert outside_role is not None
        url = reverse("users:roles-detail", kwargs={"pk": outside_role.pk})

        self.assertEqual(self.get(url).status_code, 404)
        self.assertEqual(self.delete(url).status_code, 404)
        self.assertTrue(Role.objects.filter(pk=outside_role.pk).exists())

    def test_cannot_create_a_role_in_a_foreign_hotel(self):
        response = self.post(
            reverse("users:roles-list"),
            data={"name": "Smuggled", "tenant": TENANT_2_ID, "permissions": []},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Role.objects.filter(name="Smuggled").exists())

    def test_role_list_stays_inside_the_chain(self):
        response = self.get(reverse("users:roles-list"))
        assert response.data is not None
        tenants = {str(role["tenant"]) for role in response.data if role["tenant"]}
        self.assertEqual(tenants, {TENANT_ID})

    def test_own_listing_does_not_leak_other_chain_admins(self):
        """A hotel-less caller has no colleagues; `tenant_id=None` must not match them."""
        provision_tenant_group(title="Rival", email="rival@admin.uz", password="password")

        response = self.get(reverse("users:users-list"))
        assert response.data is not None
        self.assertEqual(response.data["results"], [])


class ChainPinIntegrityTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def test_pin_without_superuser_grants_nothing(self):
        group = TenantGroup.objects.create(title="Chain")
        Tenant.objects.filter(pk=TENANT_ID).update(group=group)

        karina = User.objects.get(email="karina@gmail.com")  # ordinary user of tenant 1
        User.objects.filter(pk=karina.pk).update(tenant_group=group)
        karina.refresh_from_db()

        # The pin narrows `is_superuser`; on its own it must not widen anything.
        self.assertEqual([t.pk for t in available_tenants_qs(karina)], [karina.tenant_id])

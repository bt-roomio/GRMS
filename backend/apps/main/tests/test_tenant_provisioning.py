from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import DeviceProfile, Tenant, TenantGroup
from main.services.tenant_provisioning import provision_tenant, provision_tenant_group
from users.models import Role, User
from users.utils.tenant_access import available_tenants_qs


class TenantProvisioningTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def test_provisions_role_user_and_profiles(self):
        tenant = provision_tenant(title="Astoria", email="gm@astoria.uz", password="secret")

        role = Role.objects.get(name="TENANT_ADMIN", tenant=tenant)
        user = User.objects.get(email="gm@astoria.uz")
        self.assertEqual(user.tenant_id, tenant.id)
        self.assertIn(role, user.roles.all())
        self.assertEqual(DeviceProfile.objects.filter(tenant=tenant).count(), 3)

    def test_can_be_attached_to_a_chain(self):
        group = TenantGroup.objects.create(title="Chain")
        tenant = provision_tenant(title="Astoria", email="gm@astoria.uz", password="secret", group=group)
        self.assertEqual(tenant.group_id, group.id)

    def test_admin_api_creates_tenant_inside_a_chain(self):
        group = TenantGroup.objects.create(title="Chain")
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

        response = self.post(
            reverse("admin_panel:admin-tenant-list"),
            data={"title": "Astoria", "email": "gm@astoria.uz", "password": "secret", "group": str(group.pk)},
            format="json",
        )
        assert response.data is not None
        self.assertEqual(response.status_code, 201)
        self.assertEqual(str(Tenant.objects.get(title="Astoria").group_id), str(group.pk))


class TenantGroupProvisioningTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def test_provisions_a_pinned_superuser(self):
        group = provision_tenant_group(title="Marriott", email="owner@marriott.uz", password="secret")

        admin = User.objects.get(email="owner@marriott.uz")
        self.assertEqual(admin.tenant_group_id, group.id)
        self.assertTrue(admin.is_superuser)
        self.assertIsNone(admin.tenant_id)

    def test_chain_admin_sees_only_the_hotels_of_the_chain(self):
        group = provision_tenant_group(title="Marriott", email="owner@marriott.uz", password="secret")
        provision_tenant(title="Astoria", email="gm@astoria.uz", password="secret", group=group)

        admin = User.objects.get(email="owner@marriott.uz")
        self.assertEqual([t.title for t in available_tenants_qs(admin)], ["Astoria"])

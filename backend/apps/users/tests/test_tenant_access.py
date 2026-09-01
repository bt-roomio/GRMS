from core.tests.base import BaseTestCase
from main.models import Tenant, TenantGroup
from users.models import User
from users.utils.tenant_access import available_tenants_qs

TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"
TENANT_2_ID = "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc"


class TenantAccessTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.group = TenantGroup.objects.create(title="Chain")
        Tenant.objects.filter(pk__in=[TENANT_ID, TENANT_2_ID]).update(group=self.group)

        self.karina = User.objects.get(email="karina@gmail.com")
        self.romeo = User.objects.get(email="romeo@gmail.com")

    def pin_to_chain(self, user):
        """A chain admin is a superuser pinned to one chain."""
        user.is_superuser = True
        user.tenant_group = self.group
        user.save(update_fields=["is_superuser", "tenant_group"])
        return User.objects.get(pk=user.pk)

    def test_ordinary_user_sees_only_own_tenant(self):
        self.assertEqual([str(t.pk) for t in available_tenants_qs(self.romeo)], [TENANT_2_ID])

    def test_ordinary_user_of_a_chain_hotel_sees_only_that_hotel(self):
        self.assertEqual([str(t.pk) for t in available_tenants_qs(self.karina)], [TENANT_ID])

    def test_chain_admin_sees_the_whole_chain(self):
        tenants = available_tenants_qs(self.pin_to_chain(self.karina))
        self.assertCountEqual([str(t.pk) for t in tenants], [TENANT_ID, TENANT_2_ID])

    def test_chain_pin_narrows_a_superuser(self):
        admin = User.objects.get(email="admin@gmail.com")
        admin.tenant_group = self.group
        admin.save(update_fields=["tenant_group"])

        tenants = available_tenants_qs(User.objects.get(pk=admin.pk))
        self.assertCountEqual([str(t.pk) for t in tenants], [TENANT_ID, TENANT_2_ID])

    def test_unpinned_superuser_sees_everything(self):
        admin = User.objects.get(email="admin@gmail.com")
        self.assertEqual(available_tenants_qs(admin).count(), Tenant.objects.count())

    def test_user_without_a_tenant_sees_nothing(self):
        self.romeo.tenant = None
        self.romeo.save(update_fields=["tenant"])
        self.assertEqual(available_tenants_qs(User.objects.get(pk=self.romeo.pk)).count(), 0)

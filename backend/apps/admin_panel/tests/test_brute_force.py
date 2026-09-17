from unittest.mock import patch

from django.core.cache.backends.locmem import LocMemCache
from django.urls import reverse

from core.tests.base import BaseTestCase
from core.utils import brute_force as bf
from main.models import Tenant, TenantGroup
from users.models import User
from users.serializers.jwt_token import build_tokens_for

TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"
LOGIN = "/api/v1/users/access-token/"


class AdminUnlockTestBase(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.cache = LocMemCache("bf-admin-test", {})
        self.cache.clear()
        patcher = patch.object(bf, "security_cache", self.cache)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.victim = User.objects.filter(tenant_id=TENANT_ID, is_superuser=False).first()
        assert self.victim is not None

    def authenticate(self, user):
        tokens = build_tokens_for(User.objects.get(pk=user.pk))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    def lock_victim(self, ip="203.0.113.10"):
        """Put the account into a locked state exactly the way the middleware does."""
        email = bf.normalize_email(self.victim.email)
        bf.remember_ip(email, ip, cache=self.cache)
        self.cache.set(bf.key("attempts", LOGIN, email, ip), 5, 300)
        self.cache.set(bf.key("next_allowed", LOGIN, email, ip), bf.time.time() + 900, 900)
        return email, ip


class AdminUnlockAccessTests(AdminUnlockTestBase):
    """Access: SYS_ADMIN and TENANT_GROUP_ADMIN only, within their own scope."""

    def test_regular_user_is_forbidden(self):
        self.authenticate(self.victim)
        url = reverse("admin_panel:admin-user-lock", kwargs={"user_id": self.victim.pk})
        self.assertEqual(self.post(url, data={}, format="json").status_code, 403)
        self.assertEqual(self.get(url).status_code, 403)

    def test_anonymous_is_rejected(self):
        self.client.credentials()
        url = reverse("admin_panel:admin-user-lock", kwargs={"user_id": self.victim.pk})
        self.assertIn(self.get(url).status_code, (401, 403))

    def test_sys_admin_can_unlock(self):
        admin = User.objects.filter(is_superuser=True).first()
        assert admin is not None
        self.authenticate(admin)
        email, _ = self.lock_victim()

        url = reverse("admin_panel:admin-user-lock", kwargs={"user_id": self.victim.pk})
        response = self.post(url, data={}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(bf.get_lock_status(email, cache=self.cache)["is_locked"])

    def test_chain_admin_cannot_reach_foreign_account(self):
        group = TenantGroup.objects.create(title="Chain")
        outsider_tenant = Tenant.objects.exclude(pk=TENANT_ID).first()
        assert outsider_tenant is not None

        chain_admin = User.objects.get(email="karina@gmail.com")
        chain_admin.is_superuser = True
        chain_admin.tenant_group = group
        chain_admin.save(update_fields=["is_superuser", "tenant_group"])
        self.authenticate(chain_admin)

        foreign = User.objects.create(email="outsider@example.com", tenant=outsider_tenant, is_superuser=False)

        url = reverse("admin_panel:admin-user-lock", kwargs={"user_id": foreign.pk})
        # 404 rather than 403: a chain admin must not learn that foreign accounts exist
        self.assertEqual(self.post(url, data={}, format="json").status_code, 404)

    def test_chain_admin_can_unlock_own_chain_account(self):
        group = TenantGroup.objects.create(title="Chain")
        Tenant.objects.filter(pk=TENANT_ID).update(group=group)

        chain_admin = User.objects.get(email="karina@gmail.com")
        chain_admin.is_superuser = True
        chain_admin.tenant_group = group
        chain_admin.save(update_fields=["is_superuser", "tenant_group"])
        self.authenticate(chain_admin)

        victim = User.objects.filter(tenant_id=TENANT_ID, is_superuser=False).exclude(pk=chain_admin.pk).first()
        assert victim is not None
        self.victim = victim
        email, _ = self.lock_victim()

        url = reverse("admin_panel:admin-user-lock", kwargs={"user_id": victim.pk})
        self.assertEqual(self.post(url, data={}, format="json").status_code, 200)
        self.assertFalse(bf.get_lock_status(email, cache=self.cache)["is_locked"])


class AdminUnlockBehaviourTests(AdminUnlockTestBase):
    def setUp(self):
        super().setUp()
        admin = User.objects.filter(is_superuser=True).first()
        assert admin is not None
        self.authenticate(admin)
        self.url = reverse("admin_panel:admin-user-lock", kwargs={"user_id": self.victim.pk})

    def test_status_reports_lock_and_remaining_time(self):
        self.lock_victim()
        response = self.get(self.url)
        assert response.data is not None

        self.assertTrue(response.data["is_locked"])
        self.assertEqual(response.data["known_ips"], ["203.0.113.10"])
        lock = response.data["locks"][0]
        self.assertEqual(lock["reason"], "lockout")
        self.assertEqual(lock["endpoint"], LOGIN)
        self.assertGreater(lock["seconds_left"], 0)

    def test_status_is_clean_for_unlocked_account(self):
        response = self.get(self.url)
        assert response.data is not None
        self.assertFalse(response.data["is_locked"])
        self.assertEqual(response.data["locks"], [])

    def test_unlock_clears_every_key_kind(self):
        email, ip = self.lock_victim()
        self.cache.set(bf.window_key("1h", LOGIN, email, ip), 12, 3600)

        self.assertEqual(self.post(self.url, data={}, format="json").status_code, 200)

        for kind in bf.KINDS:
            self.assertIsNone(self.cache.get(bf.key(kind, LOGIN, email, ip)), f"{kind} was not cleared")
        self.assertIsNone(self.cache.get(bf.window_key("1h", LOGIN, email, ip)))

    def test_unlock_does_not_lift_hard_block(self):
        _, ip = self.lock_victim()
        self.cache.set(bf.hard_block_key(ip), True, None)

        self.post(self.url, data={}, format="json")

        # A permanent IP ban is set manually and lifted separately
        self.assertTrue(self.cache.get(bf.hard_block_key(ip)))

    def test_unlock_is_idempotent(self):
        self.lock_victim()
        self.assertEqual(self.post(self.url, data={}, format="json").status_code, 200)
        self.assertEqual(self.post(self.url, data={}, format="json").status_code, 200)

    def test_unknown_user_returns_404(self):
        url = reverse("admin_panel:admin-user-lock", kwargs={"user_id": "00000000-0000-0000-0000-000000000000"})
        self.assertEqual(self.post(url, data={}, format="json").status_code, 404)

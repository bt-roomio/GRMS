from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import TenantGroup
from users.models import User

TENANT_ID = "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc"
OTHER_TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"
TENANT_ROLE_ID = "d3c94703-ab5e-4926-ac52-a9bf8cf34ac6"  # Reception (tenant: ac73203f)
USER_ID = "e1fcc1ff-cce1-47e9-9952-88665815a9bd"  # angelina@gmail.com
USER_ID_2 = "b1491621-9e9c-4dba-a743-119bac358781"  # romeo@gmail.com
NON_EXISTENT_ID = "11111111-1111-1111-1111-111111111111"


class AdminTenantUsersListTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def test_list(self):
        response = self.get(reverse("admin_panel:admin-tenant-users", kwargs={"tenant_id": TENANT_ID}))
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        ids = [u["id"] for u in response.data]
        self.assertIn(USER_ID, ids)
        self.assertIn(USER_ID_2, ids)

    def test_list_tenant_not_found(self):
        response = self.get(reverse("admin_panel:admin-tenant-users", kwargs={"tenant_id": NON_EXISTENT_ID}))
        self.assertEqual(response.status_code, 404)

    def test_list_forbidden_for_non_superuser(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.angelina_token)
        response = self.get(reverse("admin_panel:admin-tenant-users", kwargs={"tenant_id": TENANT_ID}))
        self.assertEqual(response.status_code, 403)

    def test_create(self):
        # Case - missing required fields
        response = self.post(
            reverse("admin_panel:admin-tenant-users", kwargs={"tenant_id": TENANT_ID}),
            {},
        )
        self.assertEqual(response.status_code, 400)

        # Case - successful creation, returns activation_link
        response = self.post(
            reverse("admin_panel:admin-tenant-users", kwargs={"tenant_id": TENANT_ID}),
            {
                "email": "newuser@hotel.com",
                "first_name": "New",
                "last_name": "User",
                "roles": [TENANT_ROLE_ID],
                "is_active": True,
            },
            format="json",
        )
        assert response.data is not None
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["user"]["email"], "newuser@hotel.com")
        self.assertIn("activation_link", response.data)

    def test_create_with_send_activation_mail(self):
        response = self.post(
            reverse("admin_panel:admin-tenant-users", kwargs={"tenant_id": TENANT_ID}) + "?send_activation_mail=true",
            {
                "email": "mailuser@hotel.com",
                "roles": [TENANT_ROLE_ID],
                "is_active": True,
            },
            format="json",
        )
        assert response.data is not None
        self.assertEqual(response.status_code, 201)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], "Activation link sent.")

    def test_create_duplicate_email(self):
        response = self.post(
            reverse("admin_panel:admin-tenant-users", kwargs={"tenant_id": TENANT_ID}),
            {
                "email": "angelina@gmail.com",
                "roles": [TENANT_ROLE_ID],
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_tenant_not_found(self):
        response = self.post(
            reverse("admin_panel:admin-tenant-users", kwargs={"tenant_id": NON_EXISTENT_ID}),
            {"email": "ghost@hotel.com", "roles": [TENANT_ROLE_ID]},
            format="json",
        )
        self.assertEqual(response.status_code, 404)


class AdminTenantUserDetailTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def test_detail(self):
        response = self.get(
            reverse("admin_panel:admin-tenant-user-detail", kwargs={"tenant_id": TENANT_ID, "user_id": USER_ID})
        )
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], USER_ID)
        self.assertEqual(response.data["email"], "angelina@gmail.com")

    def test_detail_not_found(self):
        response = self.get(
            reverse(
                "admin_panel:admin-tenant-user-detail",
                kwargs={"tenant_id": TENANT_ID, "user_id": NON_EXISTENT_ID},
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_detail_user_from_other_tenant(self):
        # User from OTHER_TENANT_ID, not from TENANT_ID — should return 404
        other_user_id = "b5c0a9db-6082-402a-86c0-25e8f24ab19e"  # test@gmail.com (tenant: 28c81921)
        response = self.get(
            reverse(
                "admin_panel:admin-tenant-user-detail",
                kwargs={"tenant_id": TENANT_ID, "user_id": other_user_id},
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_update(self):
        response = self.put(
            reverse("admin_panel:admin-tenant-user-detail", kwargs={"tenant_id": TENANT_ID, "user_id": USER_ID_2}),
            {
                "email": "romeo_updated@gmail.com",
                "first_name": "Romeo",
                "last_name": "Updated",
                "roles": [TENANT_ROLE_ID],
                "tenant": TENANT_ID,
                "is_active": True,
            },
            format="json",
        )
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "romeo_updated@gmail.com")
        self.assertEqual(response.data["last_name"], "Updated")
        self.assertEqual(str(response.data["roles"][0]), TENANT_ROLE_ID)

    def test_update_not_found(self):
        response = self.put(
            reverse(
                "admin_panel:admin-tenant-user-detail",
                kwargs={"tenant_id": TENANT_ID, "user_id": NON_EXISTENT_ID},
            ),
            {"email": "ghost@hotel.com", "roles": [TENANT_ROLE_ID], "tenant": TENANT_ID, "is_active": True},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_forbidden_for_non_superuser(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.angelina_token)
        response = self.get(
            reverse("admin_panel:admin-tenant-user-detail", kwargs={"tenant_id": TENANT_ID, "user_id": USER_ID})
        )
        self.assertEqual(response.status_code, 403)


class AdminChangePasswordTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def url(self, user_id):
        return reverse("admin_panel:admin-user-change-password", kwargs={"user_id": user_id})

    def test_change_password(self):
        response = self.post(self.url(USER_ID), {"new_password": "NewPassword1"}, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Password changed.")
        self.assertTrue(User.objects.get(pk=USER_ID).check_password("NewPassword1"))

    def test_change_password_invalid(self):
        # Case - too short / no uppercase / no digit
        response = self.post(self.url(USER_ID), {"new_password": "weak"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_change_password_user_not_found(self):
        response = self.post(self.url(NON_EXISTENT_ID), {"new_password": "NewPassword1"}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_change_password_of_a_chain_admin(self):
        group = TenantGroup.objects.create(title="Chain")
        chain_admin = User.objects.create(
            email="chain@hotel.com", tenant_group=group, is_superuser=True, is_active=True
        )

        response = self.post(self.url(chain_admin.pk), {"new_password": "NewPassword1"}, format="json")

        self.assertEqual(response.status_code, 200)
        chain_admin.refresh_from_db()
        self.assertTrue(chain_admin.check_password("NewPassword1"))

    def test_unpinned_superuser_is_out_of_reach(self):
        # An account tied to neither a hotel nor a chain answers to nobody here.
        loner = User.objects.create(email="loner@hotel.com", is_superuser=True, is_active=True)
        response = self.post(self.url(loner.pk), {"new_password": "NewPassword1"}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_unpinned_superuser_living_in_a_hotel_is_out_of_reach(self):
        # The shape that matters: system-wide reach *and* a hotel, so the tenant
        # half of the scope would otherwise pick it up. `admin@gmail.com` is one.
        target = User.objects.get(email="admin@gmail.com")
        self.assertTrue(target.is_superuser and target.tenant_id and not target.tenant_group_id)

        response = self.post(self.url(target.pk), {"new_password": "NewPassword1"}, format="json")

        self.assertEqual(response.status_code, 404)
        target.refresh_from_db()
        self.assertFalse(target.check_password("NewPassword1"))

    def test_change_password_forbidden_for_non_superuser(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.angelina_token)
        response = self.post(self.url(USER_ID), {"new_password": "NewPassword1"}, format="json")
        self.assertEqual(response.status_code, 403)

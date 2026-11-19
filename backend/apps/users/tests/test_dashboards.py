from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Dashboard
from users.models import DashboardPosition, Role, User
from users.serializers.role import RoleSerializer
from users.serializers.user import UserSerializer


class DashboardHolderValidationTests(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "dashboard.yaml",
    )

    TEST_USER_ID = "b5c0a9db-6082-402a-86c0-25e8f24ab19e"  # tenant 1
    KARINA_ID = "e1fcc1ff-cce1-47e9-9951-88665815a9bb"  # tenant 1, TENANT_ADMIN
    TENANT_ADMIN_ROLE_ID = "bb436b2a-2ff5-4835-a264-fe27e30710e6"  # tenant 1

    def setUp(self):
        super().setUp()
        self.assigned = Dashboard.objects.get(pk="01b4ac29-32bd-4c5b-b42f-7a709d1ba68f")

    def test_global_role_cannot_hold_dashboards(self):
        payload = {"name": "Global", "permissions": [], "dashboards": [str(self.assigned.pk)]}
        serializer = RoleSerializer(data=payload, context={"tenant_id": None})
        self.assertFalse(serializer.is_valid())
        self.assertIn("dashboards", serializer.errors)

    def test_tenantless_user_cannot_hold_dashboards(self):
        user = User.objects.get(pk=self.TEST_USER_ID)
        User.objects.filter(pk=user.pk).update(tenant=None)
        user.refresh_from_db()
        serializer = UserSerializer(user, data={"dashboards": [str(self.assigned.pk)]}, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("dashboards", serializer.errors)


class MyDashboardsViewTests(BaseTestCase):
    fixtures = DashboardHolderValidationTests.fixtures

    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.karina = User.objects.get(pk=DashboardHolderValidationTests.KARINA_ID)
        # "Rule Engine Statistics" comes directly, "Thermostats" through the role: default order is by title.
        self.own = Dashboard.objects.get(pk="e91dd3e9-d109-4924-b82d-95262d4ceece")
        self.via_role = Dashboard.objects.get(pk="01b4ac29-32bd-4c5b-b42f-7a709d1ba68f")
        self.karina.dashboards.add(self.own)
        Role.objects.get(pk=DashboardHolderValidationTests.TENANT_ADMIN_ROLE_ID).dashboards.add(self.via_role)

    def ids(self, response):
        return [item["id"] for item in response.data]

    def test_list_own_and_role_dashboards(self):
        response = self.client.get(reverse("users:my-dashboards"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.ids(response), [str(self.own.pk), str(self.via_role.pk)])

    def test_no_duplicates_when_granted_twice(self):
        self.karina.dashboards.add(self.via_role)
        response = self.client.get(reverse("users:my-dashboards"))
        self.assertEqual(len(response.data), 2)

    def test_reorder(self):
        payload = {"ids": [str(self.via_role.pk), str(self.own.pk)]}
        response = self.client.put(reverse("users:my-dashboards-order"), payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.ids(response), payload["ids"])
        self.assertEqual(self.ids(self.client.get(reverse("users:my-dashboards"))), payload["ids"])

    def test_unpositioned_go_last(self):
        DashboardPosition.objects.create(user=self.karina, dashboard=self.via_role, position=0)
        response = self.client.get(reverse("users:my-dashboards"))
        self.assertEqual(self.ids(response), [str(self.via_role.pk), str(self.own.pk)])

    def test_reorder_rejects_unavailable(self):
        payload = {"ids": ["11111111-1111-1111-1111-111111111111"]}
        response = self.client.put(reverse("users:my-dashboards-order"), payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_reorder_rejects_duplicates(self):
        payload = {"ids": [str(self.own.pk), str(self.own.pk)]}
        response = self.client.put(reverse("users:my-dashboards-order"), payload, format="json")
        self.assertEqual(response.status_code, 400)

    def detail(self, dashboard):
        return self.client.get(reverse("users:my-dashboard-detail", kwargs={"pk": dashboard.pk}))

    def test_open_own_dashboard(self):
        response = self.detail(self.own)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(self.own.pk))
        self.assertIn("configuration", response.data)
        self.assertNotIn("users", response.data)
        self.assertNotIn("roles", response.data)

    def test_open_dashboard_via_role(self):
        response = self.detail(self.via_role)
        self.assertEqual(response.status_code, 200)

    def test_open_without_view_permission(self):
        # Holding the dashboard is enough; main.view_dashboard is not needed.
        self.karina.roles.clear()
        self.karina.dashboards.add(self.via_role)
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.assertFalse(User.objects.get(pk=self.karina.pk).has_perm("main.view_dashboard"))
        self.assertEqual(self.detail(self.via_role).status_code, 200)

    def test_open_not_held_dashboard(self):
        self.karina.dashboards.remove(self.own)
        self.assertEqual(self.detail(self.own).status_code, 404)

    def test_open_unauthorized(self):
        self.client.credentials()
        self.assertEqual(self.detail(self.own).status_code, 401)


class UserTenantChangeTests(BaseTestCase):
    fixtures = DashboardHolderValidationTests.fixtures

    TEST_USER_ID = DashboardHolderValidationTests.TEST_USER_ID  # tenant 1
    TENANT_2_ID = "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc"
    SYS_ADMIN_ROLE_ID = "4131460f-05d5-4597-aba5-53f34fbfc66e"  # tenant 1
    RECEPTION_ROLE_ID = "d3c94703-ab5e-4926-ac52-a9bf8cf34ac6"  # tenant 2

    def setUp(self):
        super().setUp()
        self.user = User.objects.get(pk=self.TEST_USER_ID)
        self.dashboard = Dashboard.objects.get(pk="01b4ac29-32bd-4c5b-b42f-7a709d1ba68f")  # tenant 1
        self.user.dashboards.add(self.dashboard)
        DashboardPosition.objects.create(user=self.user, dashboard=self.dashboard, position=0)
        self.url = reverse("users:users-detail", kwargs={"pk": self.TEST_USER_ID})

    def payload(self, **extra):
        return {"email": self.user.email, "roles": [self.RECEPTION_ROLE_ID], "tenant": self.TENANT_2_ID, **extra}

    def test_hotel_admin_cannot_move_user_to_foreign_hotel(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        response = self.client.put(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("tenant", response.data)
        self.user.refresh_from_db()
        self.assertNotEqual(str(self.user.tenant_id), self.TENANT_2_ID)

    def test_hotel_admin_cannot_drop_tenant(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        payload = {"email": self.user.email, "roles": [self.SYS_ADMIN_ROLE_ID], "tenant": None}
        response = self.client.put(self.url, payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("tenant", response.data)

    def test_move_checks_dashboards_against_new_hotel(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)
        response = self.client.put(self.url, self.payload(dashboards=[str(self.dashboard.pk)]), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("dashboards", response.data)

    def test_move_checks_roles_against_new_hotel(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)
        response = self.client.put(self.url, self.payload(roles=[self.SYS_ADMIN_ROLE_ID]), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("roles", response.data)

    def test_move_without_dashboards_drops_old_ones(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)
        response = self.client.put(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["dashboards"], [])
        self.assertFalse(self.user.dashboards.exists())
        self.assertFalse(self.user.dashboard_positions.exists())

    def test_same_hotel_keeps_dashboards(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        payload = {"email": self.user.email, "roles": [self.SYS_ADMIN_ROLE_ID], "tenant": str(self.user.tenant_id)}
        response = self.client.put(self.url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.user.dashboards.filter(pk=self.dashboard.pk).exists())
        self.assertTrue(self.user.dashboard_positions.exists())

    def test_tenantless_user_does_not_borrow_caller_hotel(self):
        User.objects.filter(pk=self.user.pk).update(tenant=None)
        self.user.refresh_from_db()
        caller = User.objects.get(pk=DashboardHolderValidationTests.KARINA_ID)
        request = type("Request", (), {"user": caller})()
        serializer = UserSerializer(
            self.user, data={"dashboards": [str(self.dashboard.pk)]}, partial=True, context={"request": request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("dashboards", serializer.errors)

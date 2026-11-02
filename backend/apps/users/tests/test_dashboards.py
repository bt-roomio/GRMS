from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Dashboard
from users.models import DashboardPosition, Role, User
from users.serializers.role import RoleSerializer
from users.serializers.user import UserSerializer


class UserDashboardViewTests(BaseTestCase):
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
    ROMEO_ID = "b1491621-9e9c-4dba-a743-119bac358781"  # tenant 2
    SYS_ADMIN_ROLE_ID = "4131460f-05d5-4597-aba5-53f34fbfc66e"  # tenant 1
    RECEPTION_ROLE_ID = "d3c94703-ab5e-4926-ac52-a9bf8cf34ac6"  # tenant 2

    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.assigned = Dashboard.objects.get(pk="01b4ac29-32bd-4c5b-b42f-7a709d1ba68f")
        self.unassigned = Dashboard.objects.get(pk="e91dd3e9-d109-4924-b82d-95262d4ceece")
        User.objects.get(pk=self.TEST_USER_ID).dashboards.add(self.assigned)

    def test_list_only_assigned(self):
        response = self.client.get(reverse("users:dashboards-list"))
        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data["results"]]
        self.assertEqual(ids, [str(self.assigned.pk)])
        self.assertEqual(response.data["results"][0]["users"][0]["id"], self.TEST_USER_ID)

    def test_list_unauthorized(self):
        self.client.credentials()
        response = self.client.get(reverse("users:dashboards-list"))
        self.assertEqual(response.status_code, 401)

    def test_create_assigns_holders(self):
        payload = {"title": "Reception board", "user_ids": [self.TEST_USER_ID], "role_ids": [self.SYS_ADMIN_ROLE_ID]}
        response = self.client.post(reverse("users:dashboards-list"), payload, format="json")
        self.assertEqual(response.status_code, 201)
        dashboard_id = response.data["id"]
        self.assertTrue(User.objects.get(pk=self.TEST_USER_ID).dashboards.filter(pk=dashboard_id).exists())
        self.assertTrue(Role.objects.get(pk=self.SYS_ADMIN_ROLE_ID).dashboards.filter(pk=dashboard_id).exists())
        self.assertEqual(len(response.data["roles"]), 1)

    def test_create_without_holders(self):
        response = self.client.post(reverse("users:dashboards-list"), {"title": "Orphan"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_with_foreign_user_and_role(self):
        payload = {"title": "Foreign", "user_ids": [self.ROMEO_ID], "role_ids": [self.RECEPTION_ROLE_ID]}
        response = self.client.post(reverse("users:dashboards-list"), payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("user_ids", response.data)
        self.assertIn("role_ids", response.data)

    def test_get_unassigned_not_found(self):
        response = self.client.get(reverse("users:dashboards-detail", kwargs={"pk": self.unassigned.pk}))
        self.assertEqual(response.status_code, 404)

    def test_update_replaces_holders(self):
        url = reverse("users:dashboards-detail", kwargs={"pk": self.assigned.pk})
        payload = {"title": "Thermostats", "user_ids": [], "role_ids": [self.SYS_ADMIN_ROLE_ID]}
        response = self.client.put(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.get(pk=self.TEST_USER_ID).dashboards.exists())
        self.assertTrue(Role.objects.get(pk=self.SYS_ADMIN_ROLE_ID).dashboards.filter(pk=self.assigned.pk).exists())
        self.assertEqual(response.data["users"], [])

    def test_update_cannot_drop_all_holders(self):
        url = reverse("users:dashboards-detail", kwargs={"pk": self.assigned.pk})
        response = self.client.put(url, {"title": "Thermostats", "user_ids": []}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_delete_unassigns_holders(self):
        response = self.client.delete(reverse("users:dashboards-detail", kwargs={"pk": self.assigned.pk}))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Dashboard.objects.filter(pk=self.assigned.pk).exists())
        self.assertFalse(User.objects.get(pk=self.TEST_USER_ID).dashboards.exists())

    def test_inactive_holder_hidden_and_kept(self):
        User.objects.filter(pk=self.TEST_USER_ID).update(is_active=False)
        response = self.client.get(reverse("users:dashboards-list"))
        # Its only holder is deactivated, so the dashboard no longer counts as assigned.
        self.assertEqual(response.data["results"], [])

        role = Role.objects.get(pk=self.SYS_ADMIN_ROLE_ID)
        role.dashboards.add(self.assigned)
        url = reverse("users:dashboards-detail", kwargs={"pk": self.assigned.pk})
        response = self.client.put(url, {"title": "Thermostats", "user_ids": []}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["users"], [])
        self.assertTrue(self.assigned.users.filter(pk=self.TEST_USER_ID).exists())

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
    fixtures = UserDashboardViewTests.fixtures

    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.karina = User.objects.get(pk=UserDashboardViewTests.KARINA_ID)
        # "Rule Engine Statistics" comes directly, "Thermostats" through the role: default order is by title.
        self.own = Dashboard.objects.get(pk="e91dd3e9-d109-4924-b82d-95262d4ceece")
        self.via_role = Dashboard.objects.get(pk="01b4ac29-32bd-4c5b-b42f-7a709d1ba68f")
        self.karina.dashboards.add(self.own)
        Role.objects.get(pk=UserDashboardViewTests.TENANT_ADMIN_ROLE_ID).dashboards.add(self.via_role)

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

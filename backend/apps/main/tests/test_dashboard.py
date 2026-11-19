from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Dashboard
from users.models import Role, User


class DashboardViewTests(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "dashboard.yaml",
    )

    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"

    def test_list_dashboards_success(self):
        url = reverse("main:dashboard-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)
        self.assertGreaterEqual(len(response.data["results"]), 1)

    def test_list_dashboards_permission_denied(self):
        self.client.credentials()
        url = reverse("main:dashboard-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    def test_create_dashboard_success(self):
        url = reverse("main:dashboard-list")
        payload = {
            "title": "Energy Monitor",
            "tenant": self.tenant_id,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("title", response.data)

    def test_create_dashboard_validation_error(self):
        url = reverse("main:dashboard-list")
        data = {}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("title", response.data)

    def test_get_dashboard_detail_success(self):
        dashboard = Dashboard.objects.first()
        url = reverse("main:dashboard-detail", kwargs={"pk": dashboard.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(dashboard.id))

    def test_get_dashboard_detail_not_found(self):
        url = reverse("main:dashboard-detail", kwargs={"pk": "11111111-1111-1111-1111-111111111111"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_update_dashboard_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)

        dashboard = Dashboard.objects.first()
        url = reverse("main:dashboard-detail", kwargs={"pk": dashboard.id})

        data = {
            "title": "Updated Dashboard",
            "tenant": dashboard.tenant_id,
            "configuration": {},
            "assigned_customers": "",
            "mobile_hide": False,
            "mobile_order": 2,
            "image": None,
            "external_id": dashboard.external_id,
        }

        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Updated Dashboard")

    def test_update_dashboard_validation_error(self):
        dashboard = Dashboard.objects.first()
        url = reverse("main:dashboard-detail", kwargs={"pk": dashboard.id})
        response = self.client.put(url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("title", response.data)

    def test_delete_dashboard_success(self):
        dashboard = Dashboard.objects.first()
        url = reverse("main:dashboard-detail", kwargs={"pk": dashboard.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Dashboard.objects.filter(id=dashboard.id).exists())


class DashboardHoldersTests(BaseTestCase):
    fixtures = DashboardViewTests.fixtures

    TEST_USER_ID = "b5c0a9db-6082-402a-86c0-25e8f24ab19e"  # tenant 1
    ROMEO_ID = "b1491621-9e9c-4dba-a743-119bac358781"  # tenant 2
    SYS_ADMIN_ROLE_ID = "4131460f-05d5-4597-aba5-53f34fbfc66e"  # tenant 1
    RECEPTION_ROLE_ID = "d3c94703-ab5e-4926-ac52-a9bf8cf34ac6"  # tenant 2

    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.assigned = Dashboard.objects.get(pk="01b4ac29-32bd-4c5b-b42f-7a709d1ba68f")
        self.unassigned = Dashboard.objects.get(pk="e91dd3e9-d109-4924-b82d-95262d4ceece")
        User.objects.get(pk=self.TEST_USER_ID).dashboards.add(self.assigned)

    def detail_url(self, dashboard):
        return reverse("main:dashboard-detail", kwargs={"pk": dashboard.pk})

    def test_list_includes_unassigned_with_holders(self):
        response = self.client.get(reverse("main:dashboard-list"))
        self.assertEqual(response.status_code, 200)
        by_id = {item["id"]: item for item in response.data["results"]}
        self.assertIn(str(self.unassigned.pk), by_id)
        self.assertEqual(by_id[str(self.unassigned.pk)]["users"], [])
        self.assertEqual(by_id[str(self.assigned.pk)]["users"][0]["id"], self.TEST_USER_ID)

    def test_create_without_holders(self):
        response = self.client.post(reverse("main:dashboard-list"), {"title": "Plain"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["users"], [])
        self.assertEqual(response.data["roles"], [])

    def test_create_assigns_holders(self):
        payload = {"title": "Reception board", "user_ids": [self.TEST_USER_ID], "role_ids": [self.SYS_ADMIN_ROLE_ID]}
        response = self.client.post(reverse("main:dashboard-list"), payload, format="json")
        self.assertEqual(response.status_code, 201)
        dashboard_id = response.data["id"]
        self.assertTrue(User.objects.get(pk=self.TEST_USER_ID).dashboards.filter(pk=dashboard_id).exists())
        self.assertTrue(Role.objects.get(pk=self.SYS_ADMIN_ROLE_ID).dashboards.filter(pk=dashboard_id).exists())
        self.assertEqual(len(response.data["roles"]), 1)

    def test_create_with_foreign_user_and_role(self):
        payload = {"title": "Foreign", "user_ids": [self.ROMEO_ID], "role_ids": [self.RECEPTION_ROLE_ID]}
        response = self.client.post(reverse("main:dashboard-list"), payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("user_ids", response.data)
        self.assertIn("role_ids", response.data)

    def test_update_replaces_holders(self):
        payload = {"title": "Thermostats", "user_ids": [], "role_ids": [self.SYS_ADMIN_ROLE_ID]}
        response = self.client.put(self.detail_url(self.assigned), payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.get(pk=self.TEST_USER_ID).dashboards.exists())
        self.assertTrue(Role.objects.get(pk=self.SYS_ADMIN_ROLE_ID).dashboards.filter(pk=self.assigned.pk).exists())
        self.assertEqual(response.data["users"], [])

    def test_update_without_holder_fields_keeps_them(self):
        response = self.client.put(self.detail_url(self.assigned), {"title": "Thermostats"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["users"][0]["id"], self.TEST_USER_ID)

    def test_update_can_drop_all_holders(self):
        payload = {"title": "Thermostats", "user_ids": [], "role_ids": []}
        response = self.client.put(self.detail_url(self.assigned), payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.assigned.users.exists())

    def test_delete_unassigns_holders(self):
        response = self.client.delete(self.detail_url(self.assigned))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Dashboard.objects.filter(pk=self.assigned.pk).exists())
        self.assertFalse(User.objects.get(pk=self.TEST_USER_ID).dashboards.exists())

    def test_inactive_holder_hidden_and_kept(self):
        User.objects.filter(pk=self.TEST_USER_ID).update(is_active=False)
        response = self.client.put(
            self.detail_url(self.assigned), {"title": "Thermostats", "user_ids": []}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["users"], [])
        self.assertTrue(self.assigned.users.filter(pk=self.TEST_USER_ID).exists())

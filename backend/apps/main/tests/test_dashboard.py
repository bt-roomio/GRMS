from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Dashboard


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

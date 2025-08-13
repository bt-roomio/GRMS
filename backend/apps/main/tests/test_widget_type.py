from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import WidgetType


class WidgetTypeTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml", "widget_type.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)
        self.tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"

    def test_list_widget_types_success(self):
        response = self.client.get(reverse("main:widget-type-list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)
        self.assertGreaterEqual(len(response.data["results"]), 1)

        widget = response.data["results"][0]
        self.assertEqual(widget["id"], "3610e114-0b56-40da-a5d5-38f48bbc5c4d")
        self.assertEqual(widget["name"], "Wind speed chart card")
        self.assertEqual(widget["fqn"], "wind_speed_chart_card")

    def test_create_widget_type_success(self):
        payload = {"name": "New Widget"}
        response = self.client.post(reverse("main:widget-type-list"), payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "New Widget")

        # Ensure it's in the DB
        self.assertTrue(WidgetType.objects.filter(name="New Widget").exists())

    def test_create_widget_type_missing_name(self):
        response = self.client.post(reverse("main:widget-type-list"), {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["name"], ["This field is required."])

    def test_create_widget_type_duplicate(self):
        existing = WidgetType.objects.first()
        payload = {"name": existing.name}
        response = self.client.post(reverse("main:widget-type-list"), payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "A widget type with this name already exists!")

    def test_update_widget_type_success(self):
        widget_id = WidgetType.objects.first().id
        url = reverse("main:widget-type-detail", kwargs={"pk": widget_id})
        response = self.client.put(url, {"name": "Updated Widget"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Updated Widget")

    def test_update_widget_type_duplicate_name(self):
        widgets = WidgetType.objects.all()[:2]
        if len(widgets) < 2:
            self.skipTest("Need at least 2 widgets to test duplicate name update")

        url = reverse("main:widget-type-detail", kwargs={"pk": widgets[1].id})
        response = self.client.put(url, {"name": widgets[0].name}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "A widget type with this name already exists!")

    def test_update_widget_type_missing_name(self):
        widget_id = WidgetType.objects.first().id
        url = reverse("main:widget-type-detail", kwargs={"pk": widget_id})
        response = self.client.put(url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["name"], ["This field is required."])

    def test_delete_widget_type_success(self):
        widget = WidgetType.objects.create(name="ToDelete", tenant_id=self.tenant_id)
        url = reverse("main:widget-type-detail", kwargs={"pk": widget.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(WidgetType.objects.filter(id=widget.id).exists())

    def test_get_detail_success(self):
        widget = WidgetType.objects.first()
        url = reverse("main:widget-type-detail", kwargs={"pk": widget.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(widget.id))

    def test_get_detail_not_found(self):
        url = reverse("main:widget-type-detail", kwargs={"pk": "00000000-0000-0000-0000-000000000000"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

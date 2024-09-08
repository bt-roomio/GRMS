from core.tests.base_test import BaseTestCase
from django.urls import reverse


class RoomTypeTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "groups_permissions.yaml", "users.yaml", "widget_type.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def test_list(self):
        response = self.client.get(reverse("main:widget-type-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["id"], "3610e114-0b56-40da-a5d5-38f48bbc5c4d")
        self.assertEqual(response.data["results"][0]["name"], "Wind speed chart card")
        self.assertEqual(response.data["results"][0]["fqn"], "wind_speed_chart_card")

    def test_create(self):
        response = self.client.post(reverse("main:widget-type-list"), {"name": "Amigo"})
        self.assertEqual(response.status_code, 201)

        response = self.client.post(reverse("main:widget-type-list"), {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["name"], ["This field is required."])

    def test_update(self):
        room_list = self.client.get(reverse("main:widget-type-list"))
        first_room_id = room_list.data["results"][0]["id"]
        data = {"name": "Amigo 1"}
        url = reverse("main:widget-type-detail", kwargs={"pk": first_room_id})
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)

        response = self.client.put(url, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["name"], ["This field is required."])

    def test_delete(self):
        room_list = self.client.get(reverse("main:widget-type-list"))
        first_room_id = room_list.data["results"][0]["id"]
        response = self.client.delete(reverse("main:widget-type-detail", kwargs={"pk": first_room_id}))
        self.assertEqual(response.status_code, 204)

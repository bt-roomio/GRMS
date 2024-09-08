from django.urls import reverse

from core.tests.base_test import BaseTestCase


class RoomTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "groups_permissions.yaml", "users.yaml", "room.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def test_list(self):
        response = self.client.get(reverse("main:room-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["number"], 101)
        self.assertEqual(response.data["results"][0]["floor"], "1")
        self.assertEqual(response.data["results"][0]["block"], "1")
        self.assertEqual(response.data["results"][1]["number"], 102)
        self.assertEqual(response.data["results"][1]["floor"], "2")
        self.assertEqual(response.data["results"][1]["block"], "3")

    def test_create(self):
        response = self.client.post(reverse("main:room-list"), {"number": 94, "floor": "3", "block": 3})
        self.assertEqual(response.status_code, 201)

        response = self.client.post(reverse("main:room-list"), {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["number"], ["This field is required."])
        self.assertEqual(response.data["floor"], ["This field is required."])
        self.assertEqual(response.data["block"], ["This field is required."])

    def test_delete(self):
        urls = reverse("main:room-detail", kwargs={"pk": "df77f910-2dcd-45cf-b6be-054c744561a7"})
        response = self.client.delete(urls)
        self.assertEqual(response.status_code, 204)

    def test_update(self):
        data = {
            "number": 103,
            "floor": "5",
            "block": "2",
        }
        url = reverse("main:room-detail", kwargs={"pk": "ab09aa20-77b8-457a-bfc4-5dee69790241"})
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)

        response = self.client.put(url, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["number"], ["This field is required."])
        self.assertEqual(response.data["floor"], ["This field is required."])
        self.assertEqual(response.data["block"], ["This field is required."])

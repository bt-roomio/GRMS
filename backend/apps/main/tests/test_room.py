from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Room


class RoomTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml", "room.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)

    def test_list(self):
        response = self.client.get(reverse("main:room-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 3)
        self.assertEqual(response.data["results"][0]["number"], 101)
        self.assertEqual(response.data["results"][1]["number"], 102)

    def test_create(self):
        response = self.client.post(reverse("main:room-list"), {"number": 94, "floor": "3", "block": 3})
        self.assertEqual(response.status_code, 201)

        response = self.client.post(reverse("main:room-list"), {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["number"], ["This field is required."])
        self.assertEqual(response.data["floor"], ["This field is required."])
        self.assertEqual(response.data["block"], ["This field is required."])

    def test_delete(self):
        url = reverse("main:room-detail", kwargs={"pk": "df77f910-2dcd-45cf-b6be-054c744561a7"})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

    def test_update(self):
        url = reverse("main:room-detail", kwargs={"pk": "ab09aa20-77b8-457a-bfc4-5dee69790241"})

        data = {"number": 103, "floor": "5", "block": "2", "devices": []}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)

        response = self.client.put(url, {"devices": []}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["number"], ["This field is required."])
        self.assertEqual(response.data["floor"], ["This field is required."])
        self.assertEqual(response.data["block"], ["This field is required."])

    def test_pagination(self):
        response = self.client.get(reverse("main:room-list"), {"page": 1, "size": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["count"], 3)

    def test_sorting_fields(self):
        url = reverse("main:room-list")

        response = self.client.get(url, {"sort_by": ["number"]})
        self.assertEqual(response.status_code, 200)
        numbers = [r["number"] for r in response.data["results"]]
        self.assertEqual(numbers, sorted(numbers))

        response = self.client.get(url, {"sort_by": ["-number"]})
        numbers = [r["number"] for r in response.data["results"]]
        self.assertEqual(numbers, sorted(numbers, reverse=True))

        response = self.client.get(url, {"sort_by": ["floor"]})
        floors = [r["floor"] for r in response.data["results"]]
        self.assertEqual(floors, sorted(floors))

        response = self.client.get(url, {"sort_by": ["-block"]})
        blocks = [r["block"] for r in response.data["results"]]
        self.assertEqual(blocks, sorted(blocks, reverse=True))

    def test_all_sort_fields_return_200(self):
        url = reverse("main:room-list")
        sort_fields = ["created_at", "-created_at", "number", "-number", "floor", "-floor", "block", "-block"]
        for field in sort_fields:
            with self.subTest(field=field):
                response = self.client.get(url, {"sort_by": [field]})
                self.assertEqual(response.status_code, 200)

    def test_filter_by_state_and_status(self):
        for state in dict(Room.STATE).keys():
            with self.subTest(state=state):
                response = self.client.get(reverse("main:room-list"), {"state": state})
                self.assertEqual(response.status_code, 200)

        for status in dict(Room.STATUS).keys():
            with self.subTest(status=status):
                response = self.client.get(reverse("main:room-list"), {"status": status})
                self.assertEqual(response.status_code, 200)

    def test_search_field_value(self):
        response = self.client.get(reverse("main:room-list"), {"search_field": "number", "search_value": 101})
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data["results"]), 1)

        response = self.client.get(reverse("main:room-list"), {"search_field": "number"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("search_value", response.data)

        response = self.client.get(reverse("main:room-list"), {"search_value": 101})
        self.assertEqual(response.status_code, 400)
        self.assertIn("search_field", response.data)

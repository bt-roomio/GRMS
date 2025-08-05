import uuid

from django.urls import reverse

from core.tests.base import BaseTestCase


class GuestTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "room.yaml",
        "guest.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def test_list_guests_basic(self):
        url = reverse("main:guest-list")
        response = self.client.get(url, {"room": "df77f910-2dcd-45cf-b6be-054c744561a7"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)

    def test_list_with_pagination_and_size(self):
        url = reverse("main:guest-list")
        response = self.client.get(url, {"room": "df77f910-2dcd-45cf-b6be-054c744561a7", "page": 1, "size": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["count"], 1)

    def test_list_with_sorting(self):
        url = reverse("main:guest-list")
        response = self.client.get(url, {"room": "df77f910-2dcd-45cf-b6be-054c744561a7", "sort_by": ["-name"]})
        self.assertEqual(response.status_code, 200)
        names = [g["name"] for g in response.data["results"]]
        self.assertEqual(names, sorted(names, reverse=True))

        response = self.client.get(url, {"room": "df77f910-2dcd-45cf-b6be-054c744561a7", "sort_by": ["name"]})
        names_sorted = [g["name"] for g in response.data["results"]]
        self.assertEqual(names_sorted, sorted(names_sorted))

    def test_create_guest_validation_error(self):
        response = self.client.post(reverse("main:guest-list"), {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data)
        self.assertIn("check_in", response.data)
        self.assertIn("check_out", response.data)

    def test_create_guest_success(self):
        url = reverse("main:guest-list")
        payload = {
            "name": "Guido",
            "lastname": "Van Rossum",
            "check_in": 1722332871,
            "check_out": 1722332912,
            "room": "df77f910-2dcd-45cf-b6be-054c744561a7",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Guido")
        self.assertEqual(response.data["room"], str(uuid.UUID(payload["room"])))

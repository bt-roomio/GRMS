import uuid

from django.urls import reverse

from core.tests.base_test import BaseTestCase
from main.models import Room


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

    def test_list(self):
        response = self.client.get(reverse("main:guest-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["name"], "Amigo")
        self.assertEqual(response.data["results"][0]["lastname"], "Amigoyev")
        self.assertEqual(response.data["results"][0]["birthday"], 1722332871)
        self.assertEqual(response.data["results"][0]["check_in"], 1722332912)
        self.assertEqual(response.data["results"][0]["reservation_number"], "101")
        self.assertEqual(response.data["results"][0]["room"], uuid.UUID("df77f910-2dcd-45cf-b6be-054c744561a7"))

    def test_create(self):
        response = self.client.post(reverse("main:guest-list"), {})
        self.assertEqual(response.status_code, 400)

        self.assertEqual(response.data["name"], ["This field is required."])
        self.assertEqual(response.data["check_in"], ["This field is required."])
        self.assertEqual(response.data["check_in"], ["This field is required."])

        response = self.client.post(
            reverse("main:guest-list"),
            {
                "name": "Guido",
                "lastname": "Van Rossum",
                "check_in": 1722332871,
                "check_out": 1722332912,
                "room": "df77f910-2dcd-45cf-b6be-054c744561a7",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Guido")
        self.assertEqual(response.data["lastname"], "Van Rossum")
        self.assertEqual(response.data["check_in"], 1722332871)
        self.assertEqual(response.data["check_out"], 1722332912)
        self.assertEqual(response.data["room"], uuid.UUID("df77f910-2dcd-45cf-b6be-054c744561a7"))

    def test_update(self):
        url = reverse("main:guest-detail", kwargs={"pk": "5b66af57-fb27-4c26-9986-b9994e644605"})
        data = {"name": "Guido", "room": None}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("main:room-detail", kwargs={"pk": "df77f910-2dcd-45cf-b6be-054c744561a7"}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["state"], [Room.Available])

        url = reverse("main:guest-detail", kwargs={"pk": "5b66af57-fb27-4c26-9986-b9994e644605"})
        data = {"name": "Guido", "room": "df77f910-2dcd-45cf-b6be-054c744561a7"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["room"], uuid.UUID("df77f910-2dcd-45cf-b6be-054c744561a7"))

        response = self.client.get(reverse("main:room-detail", kwargs={"pk": "df77f910-2dcd-45cf-b6be-054c744561a7"}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["state"], Room.CheckedIn)

        url = reverse("main:guest-detail", kwargs={"pk": "52d8ba26-6fac-463b-a131-c16410e42ede"})
        data = {"name": "Guido", "room": "df77f910-2dcd-45cf-b6be-054c744561a7"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["room"], uuid.UUID("df77f910-2dcd-45cf-b6be-054c744561a7"))

        response = self.client.get(reverse("main:room-detail", kwargs={"pk": "df77f910-2dcd-45cf-b6be-054c744561a7"}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["state"], Room.CheckedIn)

        url = reverse("main:guest-detail", kwargs={"pk": "52d8ba26-6fac-463b-a131-c16410e42ede"})
        data = {"name": "Guido", "room": "ab09aa20-77b8-457a-bfc4-5dee69790241"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["room"], uuid.UUID("ab09aa20-77b8-457a-bfc4-5dee69790241"))

        response = self.client.get(reverse("main:room-detail", kwargs={"pk": "ab09aa20-77b8-457a-bfc4-5dee69790241"}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["state"], Room.CheckedIn)

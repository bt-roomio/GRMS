import uuid

from django.urls import reverse

from core.tests.base_test import BaseTestCase


class DeviceTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "room.yaml",
        "customer.yaml",
        "device_profile.yaml",
        "device.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def test_list(self):
        response = self.client.get(reverse("main:device-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["name"], "DHT11 Demo Device")
        self.assertEqual(response.data["results"][0]["type"], "default")
        self.assertEqual(str(response.data["results"][0]["room"]), "df77f910-2dcd-45cf-b6be-054c744561a7")
        self.assertEqual(str(response.data["results"][0]["customer"]), "336c07bf-5613-4dfe-a74b-c4fe09f35a1e")
        self.assertEqual(str(response.data["results"][0]["tenant"]), "28c81921-f78e-4864-87d2-cec674f19d1c")
        self.assertEqual(str(response.data["results"][0]["device_profile"]), "be17d30b-9785-4415-bfa5-e7fdaf19e37c")

    def test_create(self):
        response = self.client.post(reverse("main:device-list"), {})
        self.assertEqual(response.status_code, 400)

        self.assertEqual(response.data["name"], ["This field is required."])
        self.assertEqual(response.data["type"], ["This field is required."])
        self.assertEqual(response.data["device_profile"], ["This field is required."])

        response = self.client.post(
            reverse("main:device-list"),
            {"name": "Device DHT", "type": "default", "device_profile": "be17d30b-9785-4415-bfa5-e7fdaf19e37c"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Device DHT")
        self.assertEqual(response.data["type"], "default")
        self.assertEqual(response.data["device_profile"], uuid.UUID("be17d30b-9785-4415-bfa5-e7fdaf19e37c"))

    def test_update(self):
        url = reverse("main:device-detail", kwargs={"pk": "47aef21b-6cc9-4ec5-8573-1a6f491940c0"})
        data = {"name": "Device Test"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)

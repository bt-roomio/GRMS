from django.urls import reverse
from core.tests.base import BaseTestCase


class DeviceCredentialsDetailViewTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "customer.yaml",
        "room.yaml",
        "device_profile.yaml",
        "device.yaml",
        "device_credentials.yaml"
    )

    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)

    def test_get_device_credentials_success(self):
        token = "DHT11 Demo Device"
        url = reverse("main:device-credentials-detail", kwargs={"token": token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertIn("device", response.data)

        device_data = response.data["device"]
        self.assertIn("id", device_data)
        self.assertIn("isGateway", device_data)

        self.assertEqual(device_data["id"], "47aef21b-6cc9-4ec5-8573-1a6f491940c0")

        self.assertFalse(device_data["isGateway"])

    def test_get_device_credentials_with_gateway_device(self):
        token = "Raspberry Pi Demo Device"
        url = reverse("main:device-credentials-detail", kwargs={"token": token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        device_data = response.data["device"]
        self.assertEqual(device_data["id"], "a1561fb2-e031-42ce-812a-0ce84843c0f0")

        self.assertFalse(device_data["isGateway"])

    def test_get_device_credentials_not_found(self):
        token = "non-existent-token"
        url = reverse("main:device-credentials-detail", kwargs={"token": token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_get_device_credentials_without_auth(self):
        self.client.credentials()
        token = "DHT11 Demo Device"
        url = reverse("main:device-credentials-detail", kwargs={"token": token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("device", response.data)

    def test_get_device_credentials_invalid_token(self):
        token = "invalid-token-that-does-not-exist"
        url = reverse("main:device-credentials-detail", kwargs={"token": token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_device_credentials_response_structure(self):
        token = "DHT11 Demo Device"
        url = reverse("main:device-credentials-detail", kwargs={"token": token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertIsInstance(response.data, dict)
        self.assertIn("device", response.data)

        device = response.data["device"]
        self.assertIsInstance(device, dict)
        self.assertIn("id", device)
        self.assertIn("isGateway", device)

        self.assertIsInstance(device["id"], str)
        self.assertIsInstance(device["isGateway"], bool)

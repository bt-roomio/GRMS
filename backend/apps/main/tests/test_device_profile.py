from uuid import uuid4
from django.urls import reverse
from core.tests.base import BaseTestCase
from main.models import DeviceProfile, Device


class DeviceProfileViewTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "device_profile.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"
        self.device_profile = DeviceProfile.objects.get(pk="be17d30b-9785-4415-bfa5-e7fdaf19e37c")
        self.list_url = reverse("main:device-profile-list")
        self.detail_url = reverse("main:device-profile-detail", args=[str(self.device_profile.id)])

    def test_list_device_profiles(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.json())
        self.assertIsInstance(response.json()["results"], list)
        self.assertGreaterEqual(len(response.json()["results"]), 1)

    def test_create_device_profile(self):
        payload = {
            "name": "Test Profile",
            "type": "DEFAULT",
            "state": True,
            "image": "",
            "transport_type": "DEFAULT",
            "provision_type": "DEFAULT",
            "profile_data": {},
            "description": "Created by test",
            "is_default": False,
            "default_queue_name": "Main",
            "provision_device_key": "",
            "external_id": str(uuid4()),
        }

        response = self.client.post(self.list_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["name"], "Test Profile")
        self.assertEqual(response.json()["tenant"], self.tenant_id)

    def test_retrieve_device_profile(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(self.device_profile.id))
        self.assertEqual(response.json()["name"], self.device_profile.name)

    def test_update_device_profile(self):
        updated_data = {
            "name": "Updated Profile Name",
            "type": self.device_profile.type,
            "state": True,
            "image": "",
            "transport_type": "DEFAULT",
            "provision_type": "DEFAULT",
            "profile_data": {},
            "description": "Updated via test",
            "is_default": False,
            "default_queue_name": "UpdatedQueue",
            "provision_device_key": "",
            "external_id": str(self.device_profile.external_id or uuid4()),
        }

        response = self.client.put(self.detail_url, data=updated_data, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Updated Profile Name")
        self.assertEqual(response.json()["description"], "Updated via test")

    def test_delete_device_profile_success(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, 204)

        self.device_profile.refresh_from_db()
        self.assertFalse(self.device_profile.active)

    def test_delete_device_profile_with_devices(self):
        Device.objects.create(
            name="Test Device",
            type="TEST",
            tenant=self.device_profile.tenant,
            device_profile=self.device_profile,
        )

        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "In this device_profile has the device(s).")

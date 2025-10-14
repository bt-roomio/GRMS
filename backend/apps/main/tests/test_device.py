import uuid
from unittest.mock import MagicMock, patch

from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Device, DeviceCredentials


class DeviceTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "room.yaml",
        "public_space.yaml",
        "customer.yaml",
        "device_profile.yaml",
        "device.yaml",
        "device_credentials.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.device_id = "47aef21b-6cc9-4ec5-8573-1a6f491940c0"
        self.room_without_device = "cb09aa20-77b8-457a-bfc5-5dee69790243"
        self.device_without_room = "1829490d-f742-400e-8f48-aae5155e4b27"
        self.device_profile_id = "be17d30b-9785-4415-bfa5-e7fdaf19e37c"
        self.tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"
        self.room_id = "df77f910-2dcd-45cf-b6be-054c744561a7"
        self.customer_id = "336c07bf-5613-4dfe-a74b-c4fe09f35a1e"

    def test_list_success(self):
        response = self.client.get(reverse("main:device-list"))
        self.assertEqual(response.status_code, 200)

        self.assertIn("results", response.data)
        self.assertIn("count", response.data)

        first_device = response.data["results"][2]
        self.assertEqual(first_device["name"], "DHT11 Demo Device")
        self.assertEqual(first_device["type"], "default")
        self.assertEqual(str(first_device["room"]["id"]), self.room_id)
        self.assertEqual(str(first_device["customer"]), self.customer_id)
        self.assertEqual(str(first_device["tenant"]), self.tenant_id)
        self.assertEqual(str(first_device["device_profile"]["id"]), self.device_profile_id)

        self.assertIn("credentials", first_device)
        self.assertIsNotNone(first_device["credentials"])

    def test_list_with_search_field_name(self):
        response = self.client.get(reverse("main:device-list"), {"search_field": "name", "search_value": "DHT11"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.data["results"]) >= 1)

    def test_list_with_search_field_device_profile(self):
        response = self.client.get(
            reverse("main:device-list"), {"search_field": "device_profile__name", "search_value": "default"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.data["results"]) >= 1)

    def test_list_with_status_filter(self):
        response = self.client.get(reverse("main:device-list"), {"status": "true"})
        self.assertEqual(response.status_code, 200)

    def test_list_with_sorting(self):
        response = self.client.get(reverse("main:device-list"), {"sort_by": ["name", "-created_at"]})
        self.assertEqual(response.status_code, 200)

    def test_list_with_pagination(self):
        response = self.client.get(reverse("main:device-list"), {"page": 1, "size": 10})
        self.assertEqual(response.status_code, 200)

    def test_create_missing_required_fields(self):
        response = self.client.post(reverse("main:device-list"), {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["name"], ["This field is required."])
        self.assertEqual(response.data["type"], ["This field is required."])
        self.assertEqual(response.data["device_profile"], ["This field is required."])

    def test_create_success(self):
        initial_count = Device.objects.count()
        initial_credentials_count = DeviceCredentials.objects.count()

        response = self.client.post(
            reverse("main:device-list"),
            {
                "name": "Device DHT",
                "type": "default",
                "device_profile": self.device_profile_id,
                "customer": self.customer_id,
                "room": self.room_id,
                "label": "Test Label",
                "additional_info": {"test": "data"},
                "device_data": {"config": "test"},
                "external_id": "EXT123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Device DHT")
        self.assertEqual(response.data["type"], "default")
        self.assertEqual(response.data["device_profile"]["id"], self.device_profile_id)
        self.assertEqual(response.data["label"], "Test Label")
        self.assertEqual(response.data["additional_info"], {"test": "data"})
        self.assertEqual(response.data["device_data"], {"config": "test"})
        self.assertEqual(response.data["external_id"], "EXT123")

        self.assertEqual(Device.objects.count(), initial_count + 1)

        self.assertEqual(DeviceCredentials.objects.count(), initial_credentials_count + 1)

        new_device = Device.objects.get(id=response.data["id"])
        self.assertTrue(DeviceCredentials.objects.filter(device=new_device).exists())

    @patch("main.serializers.device.has_roomio_node")
    def test_create_with_roomio_node_validation_error(self, mock_has_roomio_node):
        mock_has_roomio_node.return_value = True

        response = self.client.post(
            reverse("main:device-list"),
            {
                "name": "Device DHT",
                "type": "default",
                "device_profile": self.device_profile_id,
                "additional_info": {"roomio_node": True},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.data)
        self.assertEqual(response.data["detail"], "You already have a device with a 'roomio_node'.")

    @patch("main.serializers.device.has_roomio_node")
    def test_create_with_roomio_node_success(self, mock_has_roomio_node):
        mock_has_roomio_node.return_value = False

        response = self.client.post(
            reverse("main:device-list"),
            {
                "name": "Device DHT",
                "type": "default",
                "device_profile": self.device_profile_id,
                "additional_info": {"roomio_node": True},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["additional_info"], {"roomio_node": True})

    def test_detail_success(self):
        url = reverse("main:device-detail", kwargs={"pk": self.device_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "DHT11 Demo Device")
        self.assertEqual(response.data["type"], "default")
        self.assertEqual(str(response.data["id"]), self.device_id)

        self.assertIn("device_profile", response.data)
        self.assertIsInstance(response.data["device_profile"], dict)
        self.assertIn("name", response.data["device_profile"])

        self.assertIn("credentials", response.data)

    def test_detail_not_found(self):
        url = reverse("main:device-detail", kwargs={"pk": str(uuid.uuid4())})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_detail_inactive_device(self):
        device = Device.objects.get(pk=self.device_id)
        device.is_active = False
        device.save()

        url = reverse("main:device-detail", kwargs={"pk": self.device_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_update_success(self):
        device = Device.objects.get(pk=self.device_id)

        url = reverse("main:device-detail", kwargs={"pk": self.device_id})
        data = {
            "name": "Device Test Updated",
            "type": "custom",
            "device_profile": str(device.device_profile_id),
            "customer": str(device.customer_id) if device.customer_id else None,
            "room": str(device.room_id) if device.room_id else None,
            "tenant": str(device.tenant_id),
            "label": "Updated Label",
            "additional_info": {"updated": True},
            "device_data": {"updated_config": "test"},
            "external_id": "UPDATED123",
        }
        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Device Test Updated")
        self.assertEqual(response.data["type"], "custom")
        self.assertEqual(response.data["label"], "Updated Label")
        self.assertEqual(response.data["additional_info"], {"updated": True})
        self.assertEqual(response.data["device_data"], {"updated_config": "test"})
        self.assertEqual(response.data["external_id"], "UPDATED123")

    def test_update_not_found(self):
        url = reverse("main:device-detail", kwargs={"pk": str(uuid.uuid4())})
        data = {"name": "Device Test"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 404)

    def test_update_inactive_device(self):
        device = Device.objects.get(pk=self.device_id)
        device.is_active = False
        device.save()

        url = reverse("main:device-detail", kwargs={"pk": self.device_id})
        data = {"name": "Device Test"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 404)

    @patch("main.views.device.remove_need_sync")
    def test_delete_success(self, mock_remove_need_sync):
        url = reverse("main:device-detail", kwargs={"pk": self.device_id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)

        device = Device.objects.get(pk=self.device_id)
        self.assertFalse(device.is_active)

        mock_remove_need_sync.assert_called_once()

    def test_delete_not_found(self):
        url = reverse("main:device-detail", kwargs={"pk": str(uuid.uuid4())})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)

    def test_delete_inactive_device(self):
        device = Device.objects.get(pk=self.device_id)
        device.is_active = False
        device.save()

        url = reverse("main:device-detail", kwargs={"pk": self.device_id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)

    @patch("main.models.PublicSpace.objects.filter")
    @patch("access_manager.models.NeedSyncDevice.objects.filter")
    def test_remove_need_sync_function(self, mock_need_sync_filter, mock_public_space_filter):
        from main.views.device import remove_need_sync

        mock_need_sync_qs = MagicMock()
        mock_need_sync_filter.return_value = mock_need_sync_qs

        mock_public_space_qs = MagicMock()
        mock_public_space_filter.return_value = mock_public_space_qs

        device = Device.objects.get(pk=self.device_id)
        remove_need_sync(device)

        mock_need_sync_filter.assert_called_with(device=device, need_sync=True)
        mock_need_sync_qs.update.assert_called_with(need_sync=False)

        mock_public_space_filter.assert_called_with(device=device)
        mock_public_space_qs.update.assert_called_with(device=None)

    def test_tenant_isolation(self):
        other_tenant_device_id = "9829490d-f742-400e-8f38-aae5155e0b27"  # From different tenant

        url = reverse("main:device-detail", kwargs={"pk": other_tenant_device_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_serializer_representation_with_credentials(self):
        device = Device.objects.get(pk=self.device_id)

        if not hasattr(device, "credentials"):
            DeviceCredentials.objects.create(
                device=device, credentials_id="test-credentials", credentials_type="ACCESS_TOKEN"
            )

        url = reverse("main:device-detail", kwargs={"pk": self.device_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertIn("credentials", response.data)
        if response.data["credentials"]:
            self.assertIn("credentials_id", response.data["credentials"])
            self.assertIn("credentials_type", response.data["credentials"])

        self.assertIn("device_profile", response.data)
        self.assertIsInstance(response.data["device_profile"], dict)
        self.assertIn("name", response.data["device_profile"])

    def test_serializer_representation_without_credentials(self):
        response = self.client.post(
            reverse("main:device-list"),
            {"name": "Device Without Creds", "type": "default", "device_profile": self.device_profile_id},
            format="json",
        )

        device_id = response.data["id"]

        DeviceCredentials.objects.filter(device_id=device_id).delete()

        url = reverse("main:device-detail", kwargs={"pk": device_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["credentials"])

    def test_invalid_filter_params(self):
        response = self.client.get(
            reverse("main:device-list"), {"search_field": "invalid_field", "search_value": "test"}
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.get(reverse("main:device-list"), {"sort_by": ["invalid_field"]})
        self.assertEqual(response.status_code, 400)

    def test_edge_cases_pagination(self):
        response = self.client.get(reverse("main:device-list"), {"page": 0})
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("main:device-list"), {"page": 9999})
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("main:device-list"), {"size": 1000})
        self.assertEqual(response.status_code, 200)

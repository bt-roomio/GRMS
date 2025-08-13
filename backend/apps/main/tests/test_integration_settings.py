from django.urls import reverse

from core.tests.base import BaseTestCase


class IntegrationSettingsTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "customer.yaml",
        "room.yaml",
        "device_profile.yaml",
        "device.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)

    def test_get_success(self):
        response = self.get(reverse("main:integration-settings-detail"))
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["tenant_id"]), "28c81921-f78e-4864-87d2-cec674f19d1c")
        self.assertEqual(response.data["hoteza"], {"hotel_id": "999", "enable": True})
        self.assertEqual(response.data["PMS_type"], "FIAS")
        self.assertEqual(response.data["is_active"], True)
        self.assertEqual(response.data["integration_device"], "01b72123-dbba-4aaa-b827-d2a12eadda5a")

    def test_put_success(self):
        update_data = {
            "tenant_id": "124ed4ee-c3f2-4936-a625-8103dd25c364",
            "hoteza": {"enable": True, "hotel_id": "111"},
            "PMS_type": "FIAS",
            "is_active": True,
            "integration_device": "1829490d-f742-400e-8f48-aae5155e4b27",
        }
        response = self.put(reverse("main:integration-settings-detail"), data=update_data, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["tenant_id"]), "28c81921-f78e-4864-87d2-cec674f19d1c")
        self.assertEqual(response.data["hoteza"], update_data["hoteza"])
        self.assertEqual(response.data["PMS_type"], update_data["PMS_type"])
        self.assertEqual(response.data["is_active"], update_data["is_active"])
        self.assertEqual(response.data["integration_device"], update_data["integration_device"])

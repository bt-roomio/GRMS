from django.urls import reverse

from core.tests.base import BaseTestCase


class AlarmSettingsTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)

    def test_get_success(self):
        response = self.get(reverse("main:alarm-settings"))
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["tenant_id"]), "28c81921-f78e-4864-87d2-cec674f19d1c")
        self.assertEqual(response.data["humidity_enable"], False)
        self.assertEqual(response.data["bathroom_enable"], True)

    def test_put_success(self):
        update_data = {
            "tenant_id": "124ed4ee-c3f2-4936-a625-8103dd25c364",
            "humidity_enable": True,
            "bathroom_enable": False,
        }
        response = self.put(reverse("main:alarm-settings"), data=update_data, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["tenant_id"]), "28c81921-f78e-4864-87d2-cec674f19d1c")
        self.assertEqual(response.data["humidity_enable"], update_data["humidity_enable"])
        self.assertEqual(response.data["bathroom_enable"], update_data["bathroom_enable"])

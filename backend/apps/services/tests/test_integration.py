from django.urls import reverse

from core.tests.base import BaseTestCase


class IntegrationListViewTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "integrations.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.angelina_token)

    def test_list(self):
        response = self.get(reverse("services:integration-list"))
        self.assertEqual(response.status_code, 200)
        assert response.data is not None
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

        # Case
        response = self.get(reverse("services:integration-list"), {"page": 1, "size": 1})
        self.assertEqual(response.status_code, 200)
        assert response.data is not None
        self.assertEqual(len(response.data["results"]), 1)

        # Case
        response = self.get(reverse("services:integration-list"), {"page": 0, "size": 2})
        self.assertEqual(response.status_code, 200)
        assert response.data is not None
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

    def test_get(self):
        response = self.get(
            reverse("services:integration-detail", kwargs={"pk": "d5793548-ed8b-4ae4-872d-877cc7c2c38b"})
        )
        self.assertEqual(response.status_code, 200)
        assert response.data is not None
        self.assertEqual(response.data["name"], "Test")
        self.assertEqual(response.data["type"], "FIAS")
        self.assertEqual(response.data["description"], "Test description")
        self.assertEqual(response.data["enable"], True)
        self.assertEqual(response.data["is_active"], True)
        self.assertEqual(str(response.data["tenant"]), "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc")
        self.assertEqual(response.data["created_at"], "2025-01-01T00:00:00Z")

    def test_put(self):
        response = self.put(
            reverse(
                "services:integration-detail",
                kwargs={"pk": "d5793548-ed8b-4ae4-872d-877cc7c2c38b"},
            ),
            data={"name": "UPDATED_NAME", "type": "hoteza", "description": "UPDATED_DESCRIPTION"},
        )
        self.assertEqual(response.status_code, 200)
        assert response.data is not None
        self.assertEqual(response.data["name"], "UPDATED_NAME")
        self.assertEqual(response.data["type"], "hoteza")
        self.assertEqual(response.data["description"], "UPDATED_DESCRIPTION")
        self.assertEqual(response.data["enable"], True)
        self.assertEqual(response.data["is_active"], True)
        self.assertEqual(str(response.data["tenant"]), "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc")
        self.assertEqual(response.data["created_at"], "2025-01-01T00:00:00Z")

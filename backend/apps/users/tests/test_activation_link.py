from django.urls import reverse

from core.tests.base import BaseTestCase


class ActivationLinkTests(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.angelina_token)

    def test_activation_link(self):
        response = self.post(reverse("users:users-list"), {"email": "test@test.test"}, format="json")

        assert response.data is not None
        response = self.get(reverse("users:activation-link", kwargs={"user_id": response.data["id"]}))

        assert response is not None
        self.assertEqual(response.status_code, 200)

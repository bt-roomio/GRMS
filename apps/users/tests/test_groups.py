from django.urls import reverse

from core.tests.base_test import BaseTestCase


class GroupsTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "groups_permissions.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def test_list(self):
        response = self.client.get(reverse("users:groups-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["name"], "SYS_ADMIN")
        self.assertEqual(response.data[0]["id"], "4131460f-05d5-4597-aba5-53f34fbfc66e")

    def test_create(self):
        response = self.client.post(
            reverse("users:groups-list"),
            {"name": "Manager", "permissions": [], "tenant": "28c81921-f78e-4864-87d2-cec674f19d1c"},
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.post(reverse("users:groups-list"), {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["name"], ["This field is required."])
        self.assertEqual(response.data["tenant"], ["This field is required."])

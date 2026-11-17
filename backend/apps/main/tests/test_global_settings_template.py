from django.contrib.auth import authenticate
from django.urls import reverse

from rest_framework_simplejwt.tokens import RefreshToken

from core.tests.base import BaseTestCase
from main.models import GlobalSettingsTemplate

NON_EXISTENT_ID = "11111111-1111-1111-1111-111111111111"
TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"
TENANT_2_ID = "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc"


class GlobalSettingsTemplateTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)
        self.template = GlobalSettingsTemplate.objects.create(
            name="Default", config={"timezone": 5}, tenant_id=TENANT_ID
        )
        self.list_url = reverse("main:global-settings-template-list")
        self.detail_url = reverse("main:global-settings-template-detail", args=[self.template.pk])

    def test_list(self):
        response = self.get(self.list_url)
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        result = response.data["results"][0]
        self.assertEqual(result["name"], "Default")
        self.assertEqual(result["config"], {"timezone": 5})
        self.assertEqual(result["used"], 0)

    def test_list_search(self):
        GlobalSettingsTemplate.objects.create(name="Resort", tenant_id=TENANT_ID)
        response = self.get(self.list_url, {"search_field": "name", "search_value": "res"})
        assert response.data is not None
        self.assertEqual([t["name"] for t in response.data["results"]], ["Resort"])

    def test_create(self):
        payload = {"name": "Resort", "config": {"guest_auto_block": True}, "used": 10}
        response = self.post(self.list_url, data=payload, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["config"], {"guest_auto_block": True})
        self.assertEqual(response.data["used"], 0)
        template = GlobalSettingsTemplate.objects.get(pk=response.data["id"])
        self.assertEqual(template.created_by.email, "admin@gmail.com")  # ty: ignore
        self.assertEqual(str(template.tenant_id), TENANT_ID)

    def test_create_without_config(self):
        response = self.post(self.list_url, data={"name": "Resort"}, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["config"], {})

    def test_create_duplicate_name_is_rejected(self):
        response = self.post(self.list_url, data={"name": " default ", "config": {}}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_non_object_config_is_rejected(self):
        response = self.post(self.list_url, data={"name": "Resort", "config": [1, 2]}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_retrieve(self):
        response = self.get(self.detail_url)
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Default")

    def test_retrieve_not_found(self):
        response = self.get(reverse("main:global-settings-template-detail", args=[NON_EXISTENT_ID]))
        self.assertEqual(response.status_code, 404)

    def test_update(self):
        response = self.put(self.detail_url, data={"name": "Default", "config": {"timezone": 3}}, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, "Default")
        self.assertEqual(self.template.config, {"timezone": 3})

    def test_update_without_config_keeps_it(self):
        response = self.put(self.detail_url, data={"name": "DEFAULT"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, "DEFAULT")
        self.assertEqual(self.template.config, {"timezone": 5})

    def test_update_without_name_is_rejected(self):
        response = self.put(self.detail_url, data={"config": {"timezone": 3}}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_config_updated_at_changes_only_with_config(self):
        before = self.template.config_updated_at
        self.put(self.detail_url, data={"name": "Renamed", "config": {"timezone": 5}}, format="json")
        self.template.refresh_from_db()
        self.assertEqual(self.template.config_updated_at, before)

        self.put(self.detail_url, data={"name": "Renamed", "config": {"timezone": 3}}, format="json")
        self.template.refresh_from_db()
        self.assertGreater(self.template.config_updated_at, before)

    def test_update_to_taken_name_is_rejected(self):
        GlobalSettingsTemplate.objects.create(name="Resort", tenant_id=TENANT_ID)
        response = self.put(self.detail_url, data={"name": "resort"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_update_ignores_used(self):
        self.put(self.detail_url, data={"name": "Default", "used": 7}, format="json")
        self.template.refresh_from_db()
        self.assertEqual(self.template.used, 0)

    def test_delete(self):
        response = self.delete(self.detail_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(GlobalSettingsTemplate.objects.filter(pk=self.template.pk).exists())

    def test_tenant_admin_has_access(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.assertEqual(self.get(self.list_url).status_code, 200)
        self.assertEqual(self.post(self.list_url, data={"name": "X"}, format="json").status_code, 201)

    def test_user_without_perms_is_forbidden(self):
        user = authenticate(email="romeo@gmail.com", password="password")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")  # ty: ignore
        self.assertEqual(self.get(self.list_url).status_code, 403)
        self.assertEqual(self.get(self.detail_url).status_code, 403)
        self.assertEqual(self.post(self.list_url, data={"name": "X"}, format="json").status_code, 403)
        self.assertEqual(self.put(self.detail_url, data={"name": "X"}, format="json").status_code, 403)
        self.assertEqual(self.delete(self.detail_url).status_code, 403)


class GlobalSettingsTemplateTenantTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        user = authenticate(email="angelina@gmail.com", password="password")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")  # ty: ignore
        self.foreign = GlobalSettingsTemplate.objects.create(name="Default", tenant_id=TENANT_ID)
        self.list_url = reverse("main:global-settings-template-list")
        self.detail_url = reverse("main:global-settings-template-detail", args=[self.foreign.pk])

    def test_foreign_template_is_hidden(self):
        response = self.get(self.list_url)
        assert response.data is not None
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(self.get(self.detail_url).status_code, 404)
        self.assertEqual(self.put(self.detail_url, data={"name": "X"}, format="json").status_code, 404)
        self.assertEqual(self.delete(self.detail_url).status_code, 404)
        self.assertTrue(GlobalSettingsTemplate.objects.filter(pk=self.foreign.pk).exists())

    def test_same_name_in_another_tenant_is_allowed(self):
        response = self.post(self.list_url, data={"name": "Default"}, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 201)
        self.assertEqual(str(GlobalSettingsTemplate.objects.get(pk=response.data["id"]).tenant_id), TENANT_2_ID)

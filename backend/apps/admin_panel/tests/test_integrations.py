from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Tenant, TenantGroup
from services.models import Integration
from users.models import User
from users.serializers.jwt_token import build_tokens_for

TENANT_ID = "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc"
OTHER_TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"
NON_EXISTENT_ID = "11111111-1111-1111-1111-111111111111"


def list_url(tenant_id=TENANT_ID):
    return reverse("admin_panel:admin-tenant-integrations", kwargs={"tenant_id": tenant_id})


def detail_url(integrator, tenant_id=TENANT_ID):
    return reverse(
        "admin_panel:admin-tenant-integration-detail",
        kwargs={"tenant_id": tenant_id, "integrator": integrator},
    )


class AdminTenantIntegrationTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "integrations.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def test_list(self):
        response = self.get(list_url())
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual({row["integrator"] for row in response.data}, {"Test", "Test2"})

    def test_list_includes_disabled(self):
        """The tenant-facing API hides disabled integrations; the admin must still see them."""
        Integration.objects.filter(tenant_id=TENANT_ID, integrator="Test").update(enable=False)

        response = self.get(list_url())
        assert response.data is not None
        disabled = [row for row in response.data if row["integrator"] == "Test"]
        self.assertEqual(len(disabled), 1)
        self.assertFalse(disabled[0]["enable"])

    def test_detail(self):
        response = self.get(detail_url("Test"))
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["integrator"], "Test")
        self.assertEqual(str(response.data["tenant"]), TENANT_ID)

    def test_detail_is_case_insensitive(self):
        self.assertEqual(self.get(detail_url("test")).status_code, 200)

    def test_unknown_integrator(self):
        self.assertEqual(self.get(detail_url("nope")).status_code, 404)

    def test_unknown_tenant(self):
        self.assertEqual(self.get(list_url(NON_EXISTENT_ID)).status_code, 404)

    def test_disable(self):
        response = self.patch(detail_url("Test"), data={"enable": False}, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["enable"])

        integration = Integration.objects.get(tenant_id=TENANT_ID, integrator="Test")
        self.assertFalse(integration.enable)
        self.assertEqual(integration.updated_by.email, "admin@gmail.com")

    def test_enable(self):
        Integration.objects.filter(tenant_id=TENANT_ID, integrator="Test").update(enable=False)

        response = self.patch(detail_url("Test"), data={"enable": True}, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["enable"])
        self.assertTrue(Integration.objects.get(tenant_id=TENANT_ID, integrator="Test").enable)

    def test_enable_is_required(self):
        self.assertEqual(self.patch(detail_url("Test"), data={}, format="json").status_code, 400)

    def test_other_fields_are_read_only(self):
        response = self.patch(
            detail_url("Test"),
            data={"enable": False, "hotel_id": "666", "access_token": "leaked"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        integration = Integration.objects.get(tenant_id=TENANT_ID, integrator="Test")
        self.assertIsNone(integration.hotel_id)
        self.assertIsNone(integration.access_token)

    def test_create(self):
        response = self.post(list_url(), data={"integrator": "mews", "hotel_id": "42"}, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["integrator"], "mews")
        self.assertEqual(str(response.data["tenant"]), TENANT_ID)
        self.assertTrue(response.data["enable"], "a new integration is created switched on")

        integration = Integration.objects.get(tenant_id=TENANT_ID, integrator="mews")
        self.assertEqual(integration.hotel_id, "42")
        self.assertEqual(integration.created_by.email, "admin@gmail.com")

    def test_create_duplicate(self):
        """The unique constraint would surface as a 500, so the serializer rejects it first."""
        response = self.post(list_url(), data={"integrator": "Test"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_swagger_schema_builds(self):
        """A ref_name clash with services.IntegrationSerializer would 500 the whole docs page."""
        response = self.get(reverse("schema-json", kwargs={"format": ".json"}))
        self.assertEqual(response.status_code, 200)
        assert response.data is not None

        documented = {path for path in response.data["paths"] if "/integration/" in path}
        self.assertIn("/api/v1/admin/tenant/{tenant_id}/integration/", documented)

    def test_forbidden_for_non_superuser(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.angelina_token)
        self.assertEqual(self.get(list_url()).status_code, 403)
        self.assertEqual(self.get(detail_url("Test")).status_code, 403)
        self.assertEqual(self.patch(detail_url("Test"), data={"enable": False}, format="json").status_code, 403)
        self.assertEqual(self.post(list_url(), data={"integrator": "mews"}, format="json").status_code, 403)


class ChainAdminIntegrationScopeTest(BaseTestCase):
    """A superuser pinned to a chain toggles that chain's integrations and nothing else."""

    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "integrations.yaml",
    )

    def setUp(self):
        self.group = TenantGroup.objects.create(title="Chain")
        Tenant.objects.filter(pk=TENANT_ID).update(group=self.group)

        chain_admin = User.objects.get(email="karina@gmail.com")
        chain_admin.is_superuser = True
        chain_admin.tenant_group = self.group
        chain_admin.save(update_fields=["is_superuser", "tenant_group"])

        tokens = build_tokens_for(User.objects.get(pk=chain_admin.pk))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    def test_own_chain_is_reachable(self):
        self.assertEqual(self.get(list_url()).status_code, 200)
        self.assertEqual(self.patch(detail_url("Test"), data={"enable": False}, format="json").status_code, 200)

    def test_foreign_tenant_integrations_are_invisible(self):
        self.assertEqual(self.get(list_url(OTHER_TENANT_ID)).status_code, 404)

    def test_foreign_tenant_integration_cannot_be_toggled(self):
        response = self.patch(
            detail_url("hoteza", OTHER_TENANT_ID),
            data={"enable": False},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Integration.objects.get(tenant_id=OTHER_TENANT_ID, integrator="hoteza").enable)

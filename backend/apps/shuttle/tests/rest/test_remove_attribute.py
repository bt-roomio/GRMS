import uuid
from django.urls import reverse

from core.tests.base import BaseTestCase
from shuttle.models import AttributeKv


class ShuttleRemoveAttributeApiTests(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "customer.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "room.yaml",
        "device_profile.yaml",
        "device.yaml",
        "attribute_kv.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        # device ids to see which device is connecting
        self.dev_room_47 = uuid.UUID("47aef21b-6cc9-4ec5-8573-1a6f491940c0")

    def test_remove_attribute_success(self):
        url = reverse(
            "shuttle:remove-attribute-view",
            kwargs={"device_id": str(self.dev_room_47), "scope": "CLIENT_SCOPE"},
        )

        self.assertTrue(
            AttributeKv.objects.filter(
                entity_id=self.dev_room_47,
                attribute_type="CLIENT_SCOPE",
                attribute_key__in=["ip_address", "mac_address"],
            ).exists()
        )

        resp = self.client.delete(f"{url}?keys=ip_address,mac_address")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Removed", resp.data.get("message", ""))

        self.assertFalse(
            AttributeKv.objects.filter(
                entity_id=self.dev_room_47,
                attribute_type="CLIENT_SCOPE",
                attribute_key__in=["ip_address", "mac_address"],
            ).exists()
        )

    def test_remove_attribute_not_found_keys(self):
        url = reverse(
            "shuttle:remove-attribute-view",
            kwargs={"device_id": str(self.dev_room_47), "scope": "CLIENT_SCOPE"},
        )
        resp = self.client.delete(f"{url}?keys=does_not_exist")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.data.get("detail"), "Not found these keys!")

    def test_remove_attribute_wrong_scope(self):
        url = reverse(
            "shuttle:remove-attribute-view",
            kwargs={"device_id": str(self.dev_room_47), "scope": "SERVER_SCOPE"},
        )
        resp = self.client.delete(f"{url}?keys=ip_address")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.data.get("detail"), "Not found these keys!")

    def test_remove_attribute_missing_keys_param(self):
        url = reverse(
            "shuttle:remove-attribute-view",
            kwargs={"device_id": str(self.dev_room_47), "scope": "CLIENT_SCOPE"},
        )
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 400)

    def test_remove_attribute_invalid_device(self):
        url = reverse(
            "shuttle:remove-attribute-view",
            kwargs={"device_id": str(uuid.uuid4()), "scope": "CLIENT_SCOPE"},
        )
        resp = self.client.delete(f"{url}?keys=ip_address")
        self.assertEqual(resp.status_code, 400)
import uuid

from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Device, Tenant
from shuttle.models import Relation


class ShuttleRelationApiTests(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "customer.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "room.yaml",
        "device_profile.yaml",
        "device.yaml",
    )

    def setUp(self):
        # device ids used across tests
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.dev_a = uuid.UUID("47aef21b-6cc9-4ec5-8573-1a6f491940c0")  # DHT11 Demo Device (tenant 28c8…)
        self.dev_b = uuid.UUID("a1561fb2-e031-42ce-812a-0ce84843c0f0")  # Raspberry Pi Demo Device (tenant 28c8…)
        self.dev_other_tenant = uuid.UUID("9829490d-f742-400e-8f38-aae5155e0b27")  # CPU RAM Usage (tenant 5b2b…)
        self.tenant_main = Tenant.objects.get(pk="28c81921-f78e-4864-87d2-cec674f19d1c")

    def _mk_relation(self, from_id=None, to_id=None, **extras):
        return Relation.objects.create(
            from_id=Device.objects.get(pk=from_id or self.dev_a),
            from_type="DEVICE",
            to_id=Device.objects.get(pk=to_id or self.dev_b),
            to_type="DEVICE",
            relation_type_group="GATEWAY",
            relation_type="Contains",
            additional_info={"note": "init"},
            **extras,
        )

    # GET /relation/ without filters returns empty result (queryset=none()) but paginated
    def test_relation_list_no_filters(self):
        url = reverse("shuttle:relation-list")
        resp = self.client.get(url, {"page": 1, "size": 15})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("results", resp.data)
        self.assertEqual(resp.data["count"], 0)
        self.assertEqual(len(resp.data["results"]), 0)

    # GET /relation/?from_id=<uuid> filters by from_id (tenant restricted, active)
    def test_relation_list_filter_by_from_id(self):
        r = self._mk_relation()
        url = reverse("shuttle:relation-list")
        resp = self.client.get(url, {"from_id": str(self.dev_a)})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        item = resp.data["results"][0]
        self.assertEqual(uuid.UUID(item["from_id"]["id"]), r.from_id_id)
        self.assertEqual(uuid.UUID(item["to_id"]["id"]), r.to_id_id)

    def test_relation_list_filter_by_to_id(self):
        r = self._mk_relation()
        url = reverse("shuttle:relation-list")
        resp = self.client.get(url, {"to_id": str(self.dev_b)})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        item = resp.data["results"][0]
        self.assertEqual(uuid.UUID(item["to_id"]["id"]), r.to_id_id)

    def test_relation_list_pagination(self):
        self._mk_relation()
        url = reverse("shuttle:relation-list")
        resp = self.client.get(url, {"from_id": str(self.dev_a), "page": 1, "size": 1})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(len(resp.data["results"]), 1)

    # POST /relation/ create success; response uses nested device summaries for from_id/to_id
    def test_relation_post_create_success(self):
        url = reverse("shuttle:relation-list")
        payload = {
            "from_id": str(self.dev_a),
            "from_type": "DEVICE",
            "to_id": str(self.dev_b),
            "to_type": "DEVICE",
            "relation_type_group": "GATEWAY",
            "relation_type": "Contains",
            "additional_info": {"x": 1},
        }
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("from_id", resp.data)
        self.assertIn("to_id", resp.data)
        self.assertEqual(uuid.UUID(resp.data["from_id"]["id"]), self.dev_a)
        self.assertEqual(uuid.UUID(resp.data["to_id"]["id"]), self.dev_b)

    # POST validation error when required fields missing
    def test_relation_post_validation_error(self):
        url = reverse("shuttle:relation-list")
        resp = self.client.post(url, {}, format="json")
        self.assertEqual(resp.status_code, 400)
        for field in ["from_id", "from_type", "to_id", "to_type", "relation_type_group", "relation_type"]:
            self.assertIn(field, resp.data)

    # PUT /relation/<pk>/ updates only mutable fields (additional_info), immutables ignored
    def test_relation_put_update_additional_info_and_immutable_ignored(self):
        r = self._mk_relation()
        url = reverse("shuttle:relation-detail", kwargs={"pk": str(r.pk)})
        payload = {
            "from_id": str(self.dev_other_tenant),  # should be ignored by serializer.update()
            "from_type": "SHOULD_IGNORE",
            "to_id": str(self.dev_other_tenant),    # should be ignored
            "to_type": "SHOULD_IGNORE",
            "relation_type_group": "SHOULD_IGNORE",
            "relation_type": "SHOULD_IGNORE",
            "additional_info": {"updated": True},
        }
        resp = self.client.put(url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        data = resp.data
        self.assertEqual(uuid.UUID(data["from_id"]["id"]), self.dev_a)
        self.assertEqual(uuid.UUID(data["to_id"]["id"]), self.dev_b)
        self.assertEqual(data["additional_info"], {"updated": True})

        r.refresh_from_db()
        self.assertEqual(r.from_id_id, self.dev_a)
        self.assertEqual(r.to_id_id, self.dev_b)
        self.assertEqual(r.additional_info, {"updated": True})

    # PUT 404 when relation belongs to a different tenant via from_id tenant constraint
    def test_relation_put_404_wrong_tenant(self):
        r = Relation.objects.create(
            from_id=Device.objects.get(pk=self.dev_other_tenant),  # different tenant
            from_type="DEVICE",
            to_id=Device.objects.get(pk=self.dev_b),
            to_type="DEVICE",
            relation_type_group="GATEWAY",
            relation_type="Contains",
        )
        url = reverse("shuttle:relation-detail", kwargs={"pk": str(r.pk)})
        resp = self.client.put(url, {"additional_info": {"a": 1}}, format="json")
        self.assertEqual(resp.status_code, 404)

    # DELETE success
    def test_relation_delete_success(self):
        r = self._mk_relation()
        url = reverse("shuttle:relation-detail", kwargs={"pk": str(r.pk)})
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Relation.objects.filter(pk=r.pk).exists())

    # DELETE 404 with tenant mismatch
    def test_relation_delete_404_wrong_tenant(self):
        r = Relation.objects.create(
            from_id=Device.objects.get(pk=self.dev_other_tenant),  # different tenant
            from_type="DEVICE",
            to_id=Device.objects.get(pk=self.dev_b),
            to_type="DEVICE",
            relation_type_group="GATEWAY",
            relation_type="Contains",
        )
        url = reverse("shuttle:relation-detail", kwargs={"pk": str(r.pk)})
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 404)
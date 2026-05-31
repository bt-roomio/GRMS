import uuid
from unittest.mock import patch

from django.urls import reverse

from access_manager.models import Card, NeedSyncDevice
from core.tests.base import BaseTestCase
from main.models import Device


class SyncDeviceAPITest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "room.yaml",
        "guest.yaml",
        "public_space.yaml",
        "public_space_device.yaml",
        "customer.yaml",
        "device_profile.yaml",
        "device.yaml",
        "group.yaml",
        "group_public_space.yaml",
        "group_room.yaml",
        "staff.yaml",
        "card.yaml",
        "card_slot.yaml",
        "guest_public_space.yaml",
        "guest_card.yaml",
        "staff_card.yaml",
        "need_sync_device.yaml",
    )

    def setUp(self):
        # karina → tenant 28c8...
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)

        # Common PKs from fixtures
        self.card_staff_pk = "f3db0b43-5537-3d9e-a44b-0411ff10dcb5"  # used by StaffCard
        self.card_guest_pk = "f3db0b26-5537-3d9e-a44b-0411ff10dcb5"  # used by GuestCard
        self.device_dht11_pk = "47aef21b-6cc9-4ec5-8573-1a6f491940c0"  # room df77...
        self.device_rpi_pk = "a1561fb2-e031-42ce-812a-0ce84843c0f0"

        # Endpoint names
        self.url_get_post = reverse("access_manager:need-sync")
        self.url_del_by_pk = lambda pk: reverse("access_manager:need-sync-detail", kwargs={"pk": pk})
        self.url_del_by_device = lambda device_id: reverse(
            "access_manager:need-sync-by-device-detail", kwargs={"device_id": device_id}
        )

    # -----------------------------
    # GET /sync/ cases
    # -----------------------------
    def test_get_requires_card_id(self):
        resp = self.client.get(self.url_get_post)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("card_id", str(resp.data).lower())

    def test_get_returns_related_devices_without_need_sync_filter(self):
        # Card is linked to staff group that has access to room 101 with devices
        resp = self.client.get(self.url_get_post, {"card_id": self.card_staff_pk})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data, list)
        self.assertGreaterEqual(len(resp.data), 1)
        # Each item should at least contain id (SimpleNeedSyncDeviceSerializer adds SimpleDeviceSerializer fields)
        self.assertIn("id", resp.data[0])

    def test_get_with_need_sync_true_and_none_pending(self):
        # In fixtures need_sync=false for the only NeedSyncDevice entry
        resp = self.client.get(self.url_get_post, {"card_id": self.card_staff_pk, "need_sync": True})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data, dict)
        self.assertEqual(resp.data.get("message"), "No devices need syncing")

    def test_get_with_need_sync_false_returns_devices(self):
        resp = self.client.get(self.url_get_post, {"card_id": self.card_staff_pk, "need_sync": False})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data, list)
        self.assertGreaterEqual(len(resp.data), 1)

    # -----------------------------
    # POST /sync/ cases
    # -----------------------------
    def test_post_no_ids_or_device_ids_returns_noop(self):
        resp = self.client.post(self.url_get_post, {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["success"])
        self.assertEqual(resp.data["message"], "No devices need syncing")

    def test_post_validation_error_empty_ids(self):
        resp = self.client.post(self.url_get_post, {"ids": []}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("ids", resp.data.get("errors"))

    @patch("time.sleep", return_value=None)
    @patch("access_manager.tasks.sync_device.sync_devices_task.delay")
    def test_post_with_ids_starts_task(self, mock_delay, _sleep):
        # Create one pending NeedSyncDevice in current tenant
        card = Card.objects.get(id=self.card_staff_pk)
        device = Device.objects.get(id=self.device_dht11_pk)
        nsd = NeedSyncDevice.objects.create(
            device=device,
            card=card,
            need_sync=True,
            additional_info={"message_params": {"access": True}},
        )

        payload = {"ids": [str(nsd.id)]}
        resp = self.client.post(self.url_get_post, payload, format="json")
        self.assertEqual(resp.status_code, 202)
        self.assertTrue(resp.data["success"])
        self.assertEqual(resp.data["message"], "Device sync task started successfully")
        # delay called with (tenant_id, ids, device_ids)
        mock_delay.assert_called_once()
        args, kwargs = mock_delay.call_args
        self.assertEqual(str(args[0]), "28c81921-f78e-4864-87d2-cec674f19d1c")
        self.assertEqual(args[1], [nsd.id])
        self.assertEqual(args[2], [])

    @patch("time.sleep", return_value=None)
    @patch("access_manager.tasks.sync_device.sync_devices_task.delay")
    def test_post_with_device_ids_starts_task(self, mock_delay, _sleep):
        # Create two pending NeedSyncDevice for the same device
        card = Card.objects.get(id=self.card_staff_pk)
        device = Device.objects.get(id=self.device_dht11_pk)
        NeedSyncDevice.objects.create(device=device, card=card, need_sync=True)
        NeedSyncDevice.objects.create(device=device, card=card, need_sync=True)

        payload = {"device_ids": [self.device_dht11_pk]}
        resp = self.client.post(self.url_get_post, payload, format="json")
        self.assertEqual(resp.status_code, 202)
        mock_delay.assert_called_once()
        args, _ = mock_delay.call_args
        self.assertEqual(str(args[0]), "28c81921-f78e-4864-87d2-cec674f19d1c")
        self.assertEqual(args[1], [])
        self.assertEqual(args[2], [uuid.UUID(self.device_dht11_pk)])

    @patch("time.sleep", return_value=None)
    @patch("access_manager.tasks.sync_device.sync_devices_task.delay")
    def test_post_respects_tenant_isolation(self, mock_delay, _sleep):
        # Create a pending NeedSyncDevice for karina's tenant
        card = Card.objects.get(id=self.card_staff_pk)
        device = Device.objects.get(id=self.device_dht11_pk)  # tenant = 28c8...
        NeedSyncDevice.objects.create(device=device, card=card, need_sync=True)

        # Switch auth to angelina (tenant = ac73...)
        self.client.credentials(HTTP_AUTHORIZATION=self.angelina_token)

        # Even though device_ids matches, check_avialibility filters by tenant → returns NOOP
        resp = self.client.post(self.url_get_post, {"device_ids": [self.device_dht11_pk]}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["message"], "No devices need syncing")
        mock_delay.assert_not_called()

    # -----------------------------
    # DELETE /sync/<pk>/ cases
    # -----------------------------
    def test_delete_need_sync_detail_success(self):
        # Create one pending then delete by pk
        card = Card.objects.get(id=self.card_staff_pk)
        device = Device.objects.get(id=self.device_dht11_pk)
        nsd = NeedSyncDevice.objects.create(device=device, card=card, need_sync=True)

        resp = self.client.delete(self.url_del_by_pk(str(nsd.id)))
        self.assertEqual(resp.status_code, 200)

        nsd.refresh_from_db()
        self.assertFalse(nsd.need_sync)

    def test_delete_need_sync_detail_when_already_false(self):
        # Use fixture entry which is need_sync: false
        fixture_pk = "fe30ab6d-fa7a-42b1-bed8-fc3e668d1470"
        resp = self.client.delete(self.url_del_by_pk(fixture_pk))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Device is already syncing", str(resp.data))

    def test_delete_need_sync_detail_not_found(self):
        resp = self.client.delete(self.url_del_by_pk(str(uuid.uuid4())))
        self.assertEqual(resp.status_code, 404)

    # -----------------------------
    # DELETE /sync-by-device/<device_id>/ cases
    # -----------------------------
    def test_delete_by_device_when_none_pending(self):
        # In fixtures: an entry exists for this device but need_sync=false → expect 400
        resp = self.client.delete(self.url_del_by_device(self.device_dht11_pk))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Any need sync device not found", str(resp.data))

    def test_delete_by_device_success_multiple(self):
        card = Card.objects.get(id=self.card_staff_pk)
        device = Device.objects.get(id=self.device_dht11_pk)

        a = NeedSyncDevice.objects.create(device=device, card=card, need_sync=True)
        b = NeedSyncDevice.objects.create(device=device, card=card, need_sync=True)

        resp = self.client.delete(self.url_del_by_device(self.device_dht11_pk))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("removed_sync"), 2)

        # Verify both updated
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertFalse(a.need_sync)
        self.assertFalse(b.need_sync)

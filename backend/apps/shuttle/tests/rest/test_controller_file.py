from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from core.tests.base import BaseTestCase
from shuttle.models import Controller, ControllerFile


class ShuttleControllerFileApiTests(BaseTestCase):
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
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.url = reverse("shuttle:controller-file-view")

    def _upload(self, controllers, file_content=b"FW", file_name="firm.bin", file_type=None, status_code=200):
        payload = {
            "controllers": controllers,
            "file": SimpleUploadedFile(file_name, file_content, content_type="application/octet-stream"),
        }
        if file_type is not None:
            payload["file_type"] = file_type
        resp = self.client.post(self.url, data=payload, format="multipart")
        self.assertEqual(resp.status_code, status_code)
        return resp

    def test_upload_success_default_file_type(self):
        macs = ["AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66"]
        resp = self._upload(macs)

        self.assertIn("controllers", resp.data)
        self.assertIn("file", resp.data)
        self.assertEqual(resp.data["controllers"], macs)

        file_block = resp.data["file"]
        self.assertIn("id", file_block)
        self.assertIn("content", file_block)
        self.assertEqual(file_block["file_type"], "firmware")

        cf = ControllerFile.objects.get(pk=file_block["id"])
        self.assertEqual(cf.file_type, "firmware")
        # controllers created and linked to controller_file
        created = list(Controller.objects.filter(file_id=cf.id).order_by("mac_address").values_list("mac_address", flat=True))
        self.assertEqual(sorted(macs), created)

    def test_upload_success_custom_file_type(self):
        resp = self._upload(["AA:BB:CC:DD:EE:FF"], file_type="config")
        self.assertEqual(resp.data["file"]["file_type"], "config")
        cf = ControllerFile.objects.get(pk=resp.data["file"]["id"])
        self.assertEqual(cf.file_type, "config")

    def test_upload_with_empty_controllers_list_creates_file_only(self):
        resp = self._upload([], status_code=400)
        self.assertIn("controllers", resp.data)
        from shuttle.models import Controller, ControllerFile
        self.assertFalse(ControllerFile.objects.exists())
        self.assertFalse(Controller.objects.exists())

    def test_upload_invalid_mac_address(self):
        payload = {
            "controllers": ["INVALID-MAC", "AA:BB:CC:DD:EE:FF"],
            "file": SimpleUploadedFile("firm.bin", b"FW", content_type="application/octet-stream"),
        }
        resp = self.client.post(self.url, data=payload, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Controllers should include only mac_addresses", str(resp.data))

    def test_upload_missing_file(self):
        payload = {
            "controllers": ["AA:BB:CC:DD:EE:FF"],
            # no 'file'
        }
        resp = self.client.post(self.url, data=payload, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", resp.data)

    def test_upload_requires_controllers_field(self):
        payload = {
            # no 'controllers'
            "file": SimpleUploadedFile("firm.bin", b"FW", content_type="application/octet-stream"),
        }
        resp = self.client.post(self.url, data=payload, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("controllers", resp.data)
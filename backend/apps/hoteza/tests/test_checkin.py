from unittest.mock import patch

from hoteza.serializers.checkin import CheckInSerializer

from core.tests.base import BaseTestCase
from main.models import Guest
from services.models import Integration

HOTEZA_INTEGRATION_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
SEND_RPC = "hoteza.serializers.checkin.send_rpc_request"


class CheckInIgnorePasscodesTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "customer.yaml",
        "room.yaml",
        "device_profile.yaml",
        "device.yaml",
        "integrations.yaml",
    )

    payload = {
        "hotelId": "999",
        "roomNumber": "101",
        "guestName": "John",
        "guestFirstName": "Doe",
        "guestTitle": "Mr",
        "pmsRegNum": "REG-1",
        "arrivalDateTS": "1700000000",
        "departureDateTS": "1800000000",
        "guestLanguage": "en",
        "roomShare": "0",
        "swapFlag": "0",
        "nopost": "0",
        "profileNum": "1",
        "pin": "123456",
    }

    def check_in(self):
        serializer = CheckInSerializer(data=self.payload)
        serializer.is_valid(raise_exception=True)
        return serializer.save()

    @patch(SEND_RPC, return_value={"success": True})
    def test_ignore_passcodes_enabled(self, send_rpc):
        Integration.objects.filter(id=HOTEZA_INTEGRATION_ID).update(additional_info={"ignore_passcodes": True})

        guest = self.check_in()

        send_rpc.assert_not_called()
        self.assertNotIn("pin", Guest.objects.get(id=guest.id).additional_info)

    @patch("hoteza.serializers.checkin.get_guest_access_context")
    @patch(SEND_RPC, return_value={"success": True})
    def test_ignore_passcodes_disabled(self, send_rpc, access_context):
        access_context.return_value = {"devices": [type("Device", (), {"id": "device-1"})()]}

        guest = self.check_in()

        send_rpc.assert_called_once()
        self.assertEqual(Guest.objects.get(id=guest.id).additional_info["pin"], "123456")

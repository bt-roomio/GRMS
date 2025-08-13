from django.urls import reverse

from core.tests.base import BaseTestCase


class GeneralSettingsTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)

    def test_get_success(self):
        response = self.get(reverse("main:general-settings-detail"))
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["tenant_id"], "28c81921-f78e-4864-87d2-cec674f19d1c")
        self.assertEqual(response.data["lang"], "en")
        self.assertEqual(response.data["roomio_node_url"], "")
        self.assertEqual(response.data["timezone"], 0)
        self.assertEqual(response.data["controllers_sync"], False)
        self.assertEqual(response.data["check_in_out"], False)
        self.assertEqual(response.data["vip_status"], False)
        self.assertEqual(response.data["suite_rooms_controls_sync"], False)
        self.assertEqual(response.data["laundry"], False)
        self.assertEqual(response.data["visionline"], False)
        self.assertEqual(response.data["opera_integration"], False)
        self.assertEqual(response.data["visionline_card_system"], False)
        self.assertEqual(response.data["aperio_locks"], False)
        self.assertEqual(response.data["auto_checkout"], False)
        self.assertEqual(response.data["aggregate_db"], False)
        self.assertEqual(response.data["main_dashboard"], None)
        self.assertEqual(response.data["door_lock"], {"ving_card": False, "kaba": False})

    def test_put_success(self):
        update_data = {
            "tenant_id": "28c81921-f78e-4864-87d2-cec674f19d1c",
            "lang": "fr",
            "roomio_node_url": "http://new-url.com",
            "timezone": 1,
            "controllers_sync": True,
            "check_in_out": True,
            "vip_status": True,
            "suite_rooms_controls_sync": True,
            "laundry": True,
            "visionline": True,
            "opera_integration": True,
            "visionline_card_system": True,
            "aperio_locks": True,
            "auto_checkout": True,
            "aggregate_db": True,
            "door_lock": {"ving_card": True, "kaba": True},
        }

        response = self.put(reverse("main:general-settings-detail"), data=update_data, format="json")
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["tenant_id"], update_data["tenant_id"])
        self.assertEqual(response.data["lang"], update_data["lang"])
        self.assertEqual(response.data["roomio_node_url"], update_data["roomio_node_url"])
        self.assertEqual(response.data["timezone"], update_data["timezone"])
        self.assertEqual(response.data["controllers_sync"], update_data["controllers_sync"])
        self.assertEqual(response.data["check_in_out"], update_data["check_in_out"])
        self.assertEqual(response.data["vip_status"], update_data["vip_status"])
        self.assertEqual(response.data["suite_rooms_controls_sync"], update_data["suite_rooms_controls_sync"])
        self.assertEqual(response.data["laundry"], update_data["laundry"])
        self.assertEqual(response.data["visionline"], update_data["visionline"])
        self.assertEqual(response.data["opera_integration"], update_data["opera_integration"])
        self.assertEqual(response.data["visionline_card_system"], update_data["visionline_card_system"])
        self.assertEqual(response.data["aperio_locks"], update_data["aperio_locks"])
        self.assertEqual(response.data["auto_checkout"], update_data["auto_checkout"])
        self.assertEqual(response.data["aggregate_db"], update_data["aggregate_db"])
        self.assertEqual(response.data["door_lock"], update_data["door_lock"])

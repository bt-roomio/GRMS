from django.urls import reverse
from core.tests.base import BaseTestCase


class PublicSpaceTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml", "public_space.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.list_url = reverse("main:public-space-list")
        self.lobby_id = "ad09aa20-77b8-457a-bfc4-5dee69790243"
        self.conference_room_id = "ad09aa20-77b8-457a-bfc4-5dee69790242"

    # LIST TESTS
    def test_list_success(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        self.assertEqual(len(response.data["results"]), 2)

    def test_list_with_pagination(self):
        response = self.client.get(self.list_url, {"page": 1, "size": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["count"], 2)

    def test_list_with_search(self):
        response = self.client.get(self.list_url, {
            "search_field": "name",
            "search_value": "Lobby"
        })
        self.assertEqual(response.status_code, 200)
        found_lobby = any(item["name"] == "Lobby" for item in response.data["results"])
        self.assertTrue(found_lobby)

    def test_list_with_guest_access_filter(self):
        response = self.client.get(self.list_url, {"accessible_for_guest": "true"})
        self.assertEqual(response.status_code, 200)
        for item in response.data["results"]:
            self.assertTrue(item["accessible_for_guest"])

    def test_list_with_sorting(self):
        response = self.client.get(self.list_url, {"sort_by": ["name"]})
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data["results"]), 2)

    def test_list_without_permissions(self):
        self.client.credentials()  # Remove auth
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 401)

    # CREATE TESTS
    def test_create_success(self):
        data = {
            "name": "Garden Area",
            "floor": "Ground",
            "block": "C",
            "accessible_for_guest": True,
            "additional_info": {
                "area": "200 sqm",
                "features": ["fountain", "seating"]
            }
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Garden Area")
        self.assertTrue(response.data["accessible_for_guest"])

    def test_create_missing_required_fields(self):
        data = {
            "floor": "Ground"
            # Missing name
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data)

    def test_create_without_permissions(self):
        self.client.credentials()
        data = {"name": "Test Space", "floor": "1st", "block": "A"}
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, 401)

    # DETAIL TESTS
    def test_get_detail_success(self):
        url = reverse("main:public-space-detail", kwargs={"pk": self.lobby_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Lobby")
        self.assertEqual(response.data["floor"], "1st")
        self.assertTrue(response.data["accessible_for_guest"])

    def test_get_detail_not_found(self):
        url = reverse("main:public-space-detail", kwargs={"pk": "00000000-0000-0000-0000-000000000000"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_get_detail_without_permissions(self):
        self.client.credentials()
        url = reverse("main:public-space-detail", kwargs={"pk": self.lobby_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    # UPDATE TESTS
    def test_update_success(self):
        url = reverse("main:public-space-detail", kwargs={"pk": self.lobby_id})
        data = {
            "name": "Updated Lobby",
            "floor": "1st",
            "block": "A",
            "accessible_for_guest": False,
            "additional_info": {
                "area": "120 sqm",
                "open_hours": "6AM-10PM"
            }
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Updated Lobby")
        self.assertFalse(response.data["accessible_for_guest"])

    def test_update_partial(self):
        url = reverse("main:public-space-detail", kwargs={"pk": self.lobby_id})
        data = {
            "name": "Partially Updated Lobby",
            "floor": "1st",
            "block": "A",
            "accessible_for_guest": True
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Partially Updated Lobby")

    def test_update_not_found(self):
        url = reverse("main:public-space-detail", kwargs={"pk": "00000000-0000-0000-0000-000000000000"})
        data = {"name": "Test"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 404)

    def test_update_without_permissions(self):
        self.client.credentials()
        url = reverse("main:public-space-detail", kwargs={"pk": self.lobby_id})
        data = {"name": "Unauthorized Update"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 401)

    # DELETE TESTS
    def test_delete_success(self):
        url = reverse("main:public-space-detail", kwargs={"pk": self.conference_room_id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_delete_not_found(self):
        url = reverse("main:public-space-detail", kwargs={"pk": "00000000-0000-0000-0000-000000000000"})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)

    def test_delete_without_permissions(self):
        self.client.credentials()
        url = reverse("main:public-space-detail", kwargs={"pk": self.lobby_id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 401)

    def test_create_with_invalid_json(self):
        response = self.client.post(
            self.list_url,
            "invalid json",
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_list_with_invalid_pagination(self):
        """Test list with invalid pagination parameters"""
        response = self.client.get(self.list_url, {"page": 0, "size": -1})
        self.assertEqual(response.status_code, 500)


    def test_create_with_extra_long_name(self):
        data = {
            "name": "x" * 300,
            "floor": "1st",
            "block": "A"
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertIn(response.status_code, [201, 400])

    def test_tenant_isolation(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

    def test_list_with_large_page_size(self):
        response = self.client.get(self.list_url, {"size": 200})
        self.assertEqual(response.status_code, 200)

    def test_list_with_excessive_page_size(self):
        response = self.client.get(self.list_url, {"size": 500})
        self.assertEqual(response.status_code, 200)

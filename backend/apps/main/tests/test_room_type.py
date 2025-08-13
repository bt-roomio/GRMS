from django.urls import reverse

from core.tests.base import BaseTestCase


class RoomTypeTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "dashboard.yaml",
        "public_space.yaml",
        "room_type.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)

    def test_list(self):
        response = self.client.get(reverse("main:room-type-list"))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data["results"]), 2)

    def test_create(self):
        response = self.client.post(reverse("main:room-type-list"), {"title": "Room Type"})
        self.assertEqual(response.status_code, 201)

        response = self.client.post(reverse("main:room-type-list"), {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["title"], ["This field is required."])

    def test_delete(self):
        response = self.client.get(reverse("main:room-type-list"))
        room_id = response.data["results"][0]["id"]

        response = self.client.delete(reverse("main:room-type-detail", kwargs={"pk": room_id}))
        self.assertEqual(response.status_code, 204)

    def test_update(self):
        response = self.client.get(reverse("main:room-type-list"))
        room_id = response.data["results"][0]["id"]
        url = reverse("main:room-type-detail", kwargs={"pk": room_id})

        update_data = {"title": "Updated Room Type"}
        response = self.client.put(url, update_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Updated Room Type")

        response = self.client.put(url, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["title"], ["This field is required."])

    def test_filter_by_title(self):
        url = reverse("main:room-type-list") + "?search_field=title&search_value=Luxury"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all("Luxury" in r["title"] for r in response.data["results"]))

    def test_connect_room_type_to_public_spaces(self):
        response = self.client.get(reverse("main:room-type-list"))
        self.assertEqual(response.status_code, 200)
        room_type = response.data["results"][0]
        room_type_id = room_type["id"]

        payload = {
            "title": room_type["title"],
            "public_spaces_ids": ["ad09aa20-77b8-457a-bfc4-5dee69790243", "ad09aa20-77b8-457a-bfc4-5dee69790242"],
        }

        url = reverse("main:room-type-detail", kwargs={"pk": room_type_id})
        response = self.client.put(url, data=payload, format="json")
        self.assertEqual(response.status_code, 200)

        public_spaces = response.data.get("public_spaces", [])
        self.assertEqual(len(public_spaces), 2)

        ids = {ps["id"] for ps in public_spaces}
        self.assertSetEqual(ids, {"ad09aa20-77b8-457a-bfc4-5dee69790243", "ad09aa20-77b8-457a-bfc4-5dee69790242"})

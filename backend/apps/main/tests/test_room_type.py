from core.tests.base_test import BaseTestCase
from django.urls import reverse


class RoomTypeTest(BaseTestCase):
	fixtures = ("tenant_profile.yaml", "tenant.yaml", "users.yaml", "room_type.yaml")

	def setUp(self):
		self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

	def test_list(self):
		response = self.client.get(reverse("main:room-type-list"))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["results"][0]["id"], "deb5db89-b9cf-4aee-989d-4a7a7bdeb096")
		self.assertEqual(response.data["results"][0]["title"], "Luxury")
		self.assertEqual(response.data["results"][0]["check_in_out_address"], None)
		self.assertEqual(response.data["results"][0]["check_in_value"], None)
		self.assertEqual(response.data["results"][0]["check_out_value"], None)

	def test_create(self):
		response = self.client.post(reverse("main:room-type-list"), {"title": "Room Type"})
		self.assertEqual(response.status_code, 201)

		response = self.client.post(reverse("main:room-type-list"), {})
		self.assertEqual(response.status_code, 400)
		self.assertEqual(response.data["title"], ["This field is required."])

	def test_delete(self):
		room_list = self.client.get(reverse("main:room-type-list"))
		first_room_id = room_list.data["results"][0]["id"]

		response = self.client.delete(reverse("main:room-type-detail", kwargs={"pk": first_room_id}))
		self.assertEqual(response.status_code, 204)

	def test_update(self):
		room_list = self.client.get(reverse("main:room-type-list"))
		first_room_id = room_list.data["results"][0]["id"]
		data = {"title": "Room Type Updated"}
		url = reverse("main:room-type-detail", kwargs={"pk": first_room_id})
		response = self.client.put(url, data, format="json")
		self.assertEqual(response.status_code, 200)

		response = self.client.put(url, {})
		self.assertEqual(response.status_code, 400)
		self.assertEqual(response.data["title"], ["This field is required."])

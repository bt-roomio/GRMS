from core.tests.base_test import BaseTestCase
from django.urls import reverse


class RoomTypeTest(BaseTestCase):
	fixtures = ("tenant_profile.yaml", "tenant.yaml", "users.yaml", "widget_type.yaml")

	def setUp(self):
		self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

	def test_list(self):
		response = self.client.get(reverse("main:widget-type-list"))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["results"][0]["id"], "3610e114-0b56-40da-a5d5-38f48bbc5c4d")
		self.assertEqual(response.data["results"][0]["name"], "Wind speed chart card")
		self.assertEqual(str(response.data["results"][0]["tenant"]), "28c81921-f78e-4864-87d2-cec674f19d1c")
		self.assertEqual(response.data["results"][0]["fqn"], "wind_speed_chart_card")

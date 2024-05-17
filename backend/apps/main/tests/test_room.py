from django.urls import reverse
from core.tests.base_test import BaseTestCase


class RoomTest(BaseTestCase):
    fixtures = ('tenant_profile.yaml', 'tenant.yaml', 'users.yaml', 'room.yaml')

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)


    def test_list(self):
        response = self.client.get(reverse('main:room-list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['room_number'], 101)
        self.assertEqual(response.data['results'][0]['floor'], '1')
        self.assertEqual(response.data['results'][0]['block'], '1')
        self.assertEqual(response.data['results'][1]['room_number'], 102)
        self.assertEqual(response.data['results'][1]['floor'], '2')
        self.assertEqual(response.data['results'][1]['block'], '3')

    def test_create(self):
        response = self.client.post(reverse('main:room-list'), {'room_number': 94, 'floor': '3', 'block': 3})
        self.assertEqual(response.status_code, 201)

        response = self.client.post(reverse('main:room-list'), {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["room_number"], ["This field is required."])
        self.assertEqual(response.data["floor"], ["This field is required."])
        self.assertEqual(response.data["block"], ["This field is required."])

    def test_delete(self):
        room_list = self.client.get(reverse('main:room-list'))
        first_room_id = room_list.data['results'][0]['id']
        response = self.client.delete(reverse('main:room-detail', kwargs={"pk": first_room_id}))
        self.assertEqual(response.status_code, 204)

    def test_update(self):
        room_list = self.client.get(reverse('main:room-list'))
        first_room_id = room_list.data['results'][0]['id']
        data = {
            'room_number': 103,
            'floor': '5',
            'block': '2',
        }
        url = reverse('main:room-detail', kwargs={"pk": first_room_id})
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)

        response = self.client.put(url, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["room_number"], ["This field is required."])
        self.assertEqual(response.data["floor"], ["This field is required."])
        self.assertEqual(response.data["block"], ["This field is required."])

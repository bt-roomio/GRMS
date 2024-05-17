from django.urls import reverse
from core.tests.base_test import BaseTestCase


class GeneralSettingsTest(BaseTestCase):
    fixtures = ('tenant_profile.yaml', 'tenant.yaml', 'users.yaml', 'room.yaml')

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)

    def test_list(self):
        response = self.client.get(reverse('main:general-settings-detail'))
        self.assertEqual(response.data['lang'], 'en')
        self.assertEqual(response.data['timezone'], 0)
        self.assertEqual(response.data['check_in_out'], False)
        self.assertEqual(str(response.data['tenant_id']), '28c81921-f78e-4864-87d2-cec674f19d1c')

    def test_update(self):
        response = self.client.put(reverse('main:general-settings-detail'), {'lang': 'ru'})
        self.assertEqual(str(response.data['tenant_id']), '28c81921-f78e-4864-87d2-cec674f19d1c')
        self.assertEqual(response.data['lang'], 'ru')

import json
from pprint import pprint
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import authenticate


class BaseTestCase(APITestCase):
    @property
    def bearer_token(self):
        user = authenticate(email='admin@gmail.com', password='password')
        if user:
            refresh = RefreshToken.for_user(user)
            return {"HTTP_AUTHORIZATION": f'Bearer {refresh.access_token}'}

        return {}

    def dump(self, response):
        print('-' * 40)
        print('Response:', response.status_code)
        pprint(json.loads(json.dumps(response.data)))
        print('-' * 40)

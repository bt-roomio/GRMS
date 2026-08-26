import json
from pprint import pprint
from typing import cast

from django.contrib.auth import authenticate

from rest_framework.response import Response
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken


class BaseTestCase(APITestCase):
    client: APIClient  # type: ignore[assignment]

    @property
    def bearer_token(self):
        user = authenticate(email="admin@gmail.com", password="password")
        if not user:
            return ""

        refresh = cast(RefreshToken, RefreshToken.for_user(user))
        return f"Bearer {refresh.access_token}"

    @property
    def angelina_token(self):
        user = authenticate(email="angelina@gmail.com", password="password")
        if not user:
            return ""

        refresh = cast(RefreshToken, RefreshToken.for_user(user))
        return f"Bearer {refresh.access_token}"

    @property
    def karina_token(self):
        user = authenticate(email="karina@gmail.com", password="password")
        if not user:
            return ""

        refresh = cast(RefreshToken, RefreshToken.for_user(user))
        return f"Bearer {refresh.access_token}"

    def dump(self, response):
        print("-" * 40)
        print("Response:", response.status_code)
        pprint(json.loads(json.dumps(response.data)))
        print("-" * 40)

    def get(self, *args, **kwargs):
        return cast(Response, self.client.get(*args, **kwargs))

    def post(self, *args, **kwargs):
        return cast(Response, self.client.post(*args, **kwargs))

    def put(self, *args, **kwargs):
        return cast(Response, self.client.put(*args, **kwargs))

    def patch(self, *args, **kwargs):
        return cast(Response, self.client.patch(*args, **kwargs))

    def delete(self, *args, **kwargs):
        return cast(Response, self.client.delete(*args, **kwargs))

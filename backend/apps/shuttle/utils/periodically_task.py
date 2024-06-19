import asyncio

from django.conf import settings
from jwt import decode as jwt_decode

from shuttle.utils.response import response

from jwt import InvalidSignatureError, ExpiredSignatureError, DecodeError


async def periodically_task(seconds: int, self, func, *args):
    while True:
        try:
            token = self.data.get("authCmd", {}).get("token")
            print(token)
            if self.data.get("authCmd") and token:
                data = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            if not self.data.get("authCmd"):
                await self.send_json(response({}, 0, 401, "Token is invalid or expired!"))
                return
            await func(*args)
            await asyncio.sleep(seconds)

        except (TypeError, KeyError, InvalidSignatureError, ExpiredSignatureError, DecodeError):
            await self.send_json(response({}, 0, 401, "Token is invalid or expired!"))
            return

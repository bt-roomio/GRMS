import json
from django.conf import settings


from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.auth import database_sync_to_async
from jwt import decode as jwt_decode
from shuttle.utils.response import response
from jwt import InvalidSignatureError, ExpiredSignatureError, DecodeError

from users.models import User


@database_sync_to_async
def get_user(data):
    return User.objects.get(id=data["user_id"])


class BaseConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context = {}
        self.tasks = {}

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        if text_data:
            try:
                self.data = json.loads(text_data)
            except json.JSONDecodeError:
                await self.send_json({"error": "Invalid JSON format"})
                return

        try:
            token = self.data.get("authCmd", {}).get("token")
            if self.data.get("authCmd") and token:
                data = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                user = await get_user(data)
                self.scope["user"] = user
                self.context["authCmd"] = self.data.get("authCmd")

            if not self.data.get("authCmd"):
                await self.send_json(response({}, 0, 401, "Token is invalid or expired!"))
                return

            await self.receive_json(self.data)
        except (TypeError, KeyError, InvalidSignatureError, ExpiredSignatureError, DecodeError):
            await self.send_json(response({}, 0, 401, "Token is invalid or expired!"))
            return

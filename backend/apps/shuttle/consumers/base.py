import asyncio
import json

from channels.auth import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from jwt import DecodeError, ExpiredSignatureError, InvalidSignatureError
from jwt import decode as jwt_decode
from shuttle.utils.response import response
from users.models import User


@database_sync_to_async
def get_user(data):
    return User.objects.get(id=data["user_id"])


class BaseConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context = {}
        self.tasks = {}  # For storing periodically tasks
        self.task_params = {}  # Store parameters for tasks
        self.has_expired = False

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        """
        - checking for correct json data
        - checking for token and set user in scope
        """
        if text_data:
            try:
                self.data = json.loads(text_data)
            except json.JSONDecodeError:
                await self.send_json({"error": "Invalid JSON format"})
                return

        try:
            authCmd = self.data.get("authCmd", {})
            token = authCmd.get("token")
            if authCmd and token:
                checked_token = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                self.context["authCmd"] = self.data.get("authCmd")

                self.scope["user"] = await get_user(checked_token)

                self.context["has_expired"] = False

                # Resume tasks after successful re-authentication
                await self.resume_tasks()

            if not self.context.get("authCmd"):
                self.context["has_expired"] = True
                await self.send_json(response({}, 0, 401, "Token is invalid or expired!"))
                return

            await self.receive_json(self.data)
        except (TypeError, KeyError, InvalidSignatureError, ExpiredSignatureError, DecodeError) as err:
            self.context["has_expired"] = True
            await self.send_json(response({}, 0, 401, str(err)))
            return

    async def periodically_task(self, seconds: int, func, *args):
        while True:
            try:
                authCmd = self.context.get("authCmd", {})
                token = authCmd.get("token")

                if self.context.get("has_expired"):
                    return

                if not authCmd:
                    await self.send_json(response({}, 0, 401, "Token is invalid or expired!"))
                    return

                if authCmd and token:
                    checked_token = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])

                self.context.update({"has_expired": False})
                result = await func(*args)
                print(result)
                await self.send_json(result)
                await asyncio.sleep(seconds)

            except (TypeError, KeyError, InvalidSignatureError, ExpiredSignatureError, DecodeError) as err:
                self.context.update({"has_expired": True})
                await self.send_json(response({}, 0, 401, str(err)))
                return

    async def resume_tasks(self):
        for task_key, func in self.task_params.items():
            self.tasks[task_key] = asyncio.create_task(func())

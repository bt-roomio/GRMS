import asyncio
import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from jwt import DecodeError, ExpiredSignatureError, InvalidSignatureError
from jwt import decode as jwt_decode
from shuttle.utils.response import response
from users.utils.get_user import get_user


class BaseConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = {}
        self.context = {"has_expired": True}
        self.tasks = {}
        self.task_params = {}
        self.last_cmds = []
        self.interval = settings.WS_INTERVAL
        self.connectors = []

    async def disconnect(self, code):
        for task in self.tasks.values():
            task.cancel()
        self.reset_state()
        await super().disconnect(code)

    def reset_state(self):
        self.data = {}
        self.context = {"has_expired": True}
        self.tasks.clear()
        self.task_params.clear()
        self.last_cmds.clear()

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        if text_data:
            try:
                self.data = json.loads(text_data)
            except json.JSONDecodeError:
                await self.send_json({"error": "Invalid JSON format"})
                return

        auth_cmd = self.data.get("authCmd", {})

        if auth_cmd.get("token"):
            try:
                checked_token = jwt_decode(auth_cmd.get("token"), settings.SECRET_KEY, algorithms=["HS256"])
                self.scope["user"] = await get_user(checked_token)
                self.context.update({"authCmd": auth_cmd, "has_expired": False})
                await self.resume_tasks()
            except (InvalidSignatureError, ExpiredSignatureError, DecodeError) as err:
                await self.send_json(response({}, 0, 401, str(err)))
                return

        if self.context["has_expired"]:
            await self.send_json(response({}, 0, 401, "Token is invalid or expired!"))
            return

        await self.receive_json(self.data)

    async def periodically_task(self, func, *args, temp_index=None):
        index = temp_index or 0
        while not self.context["has_expired"]:
            try:
                result = await func(*args)
                if result not in self.last_cmds:
                    self.last_cmds.append(result)
                    await self.send_json(result)

                index += 1
                if index >= self.interval:
                    index = temp_index or 1
                    await self.send_json(result)
                await asyncio.sleep(1)
            except (InvalidSignatureError, ExpiredSignatureError, DecodeError) as err:
                self.context["has_expired"] = True
                await self.send_json(response({}, 0, 401, str(err)))
                return

    async def resume_tasks(self):
        for task_key, func in self.task_params.items():
            self.tasks[task_key] = asyncio.create_task(func())

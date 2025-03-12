import asyncio
import logging
import traceback

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from jwt import ExpiredSignatureError
from jwt import decode as jwt_decode

from core.utils.snake_case import convert_to_snake
from shuttle.utils.response import response
from users.utils.get_user import get_user

logger = logging.getLogger("main")


class BaseConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tasks = {}
        self.token = ""
        self.user = None

    async def cancel_task(self, task_key):
        """
        Safely cancel a task and remove it from the task list.
        """
        task_metadata = self.tasks.get(task_key)
        if task_metadata:
            task = task_metadata.get("task")
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"Task {task_key} cancelled successfully.")
            del self.tasks[task_key]

    async def resume_tasks(self):
        """
        Resume tasks after the token is updated.
        """
        for task_key, val in self.tasks.items():
            if val["stopped"]:
                func = val["func"]
                self.tasks[task_key]["task"] = asyncio.create_task(self.send_periodic_data(func))
                val["stopped"] = False

    async def disconnect(self, code):
        """
        - Cancel all tasks
        - Clear data, context, tasks, task_params
        """
        for task_key in list(self.tasks.keys()):
            await self.cancel_task(task_key)
        await super().disconnect(code)

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        try:
            data = await self.decode_json(text_data)
            await self.validate_data(data)
            converted_data = convert_to_snake(data)
            await self.auth(converted_data)
            await self.receive_json(converted_data, **kwargs)

        except ExpiredSignatureError as err:
            await self.send_json(response({}, 0, 401, str(err)))

        except Exception as err:
            tb = traceback.format_exc()
            logger.warning(f"Error occurred: {err}")
            logger.warning(f"Traceback: {tb}")
            await self.send_json(response({}, None, 400, str(err)))

    async def auth(self, data={}):
        """
        Checking for token, tenant and sets user
        """

        auth_cmd = data.get("auth_cmd", {})
        token = auth_cmd.get("token")
        self.token = token or self.token
        if not self.token:
            raise ExpiredSignatureError("Token not found!")

        checked_token = jwt_decode(self.token, settings.SECRET_KEY, algorithms=["HS256"])
        self.user = await get_user(checked_token)

        if not self.user.tenant_id:
            raise ValueError("User doesn't have tenant!")

        await self.resume_tasks()

    async def send_periodic_data(self, func, sleep_time=5):
        try:
            while True:
                if not await self.validate_auth():
                    if self.token:
                        await self.send_json(response({}, 0, 401, "User is not authenticated. Stopping periodic data."))
                    self.token = ""
                    break

                result = func()
                if asyncio.iscoroutine(result):
                    result = await result

                await self.send_json(result)
                await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            pass

    async def validate_auth(self):
        try:
            if not self.token:
                raise ExpiredSignatureError("Missing authentication token.")

            jwt_decode(self.token, settings.SECRET_KEY, algorithms=["HS256"])
        except Exception:
            for _, val in self.tasks.items():
                val["stopped"] = True
            return False
        return True

    async def validate_data(self, data):
        if not data:
            raise ValueError("content is empty!")
        if not isinstance(data, dict):
            raise ValueError("content is not dict!")
        if data.get("cmds") and not isinstance(data.get("cmds"), list):
            raise ValueError("cmds is not list")

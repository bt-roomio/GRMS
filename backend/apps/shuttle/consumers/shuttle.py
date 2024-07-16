import asyncio

from shuttle.consumers.aggregations.attribute_kv import attribute_kv
from shuttle.consumers.aggregations.latest_telemetry import latest_telemetry
from shuttle.consumers.aggregations.ts_kv_history import history_telemetery
from shuttle.consumers.base import BaseConsumer
from shuttle.models import AttributeKv
from shuttle.utils.periodically_task import periodically_task
from shuttle.utils.response import response


class ShuttleConsumer(BaseConsumer):
    async def receive_json(self, content, **kwargs):
        cmds = content.get("cmds")
        user = self.scope["user"]

        if not user.tenant_id:
            await self.send_json(response({}, 0, 1, "There is not tenant in user!"))
            return

        if not isinstance(cmds, list):
            await self.send_json(response({}, 0, 1, "`cmds` must be a list!"))
            return

        for cmd in cmds:
            cmd_id = cmd.get("cmdId")
            task_key = f"cmdId-{cmd_id}"

            """
            - Latest Telemetry
            """
            if (
                cmd.get("type") == "TIMESERIES"
                and cmd.get("scope") == "LATEST_TELEMETRY"
                and cmd.get("entityType") == "DEVICE"
            ):
                func = lambda: periodically_task(3, self, latest_telemetry, cmd, user, self.send_json)
                self.task_params[task_key] = func
                self.tasks[task_key] = asyncio.create_task(func())

            if cmd.get("type") == "TIMESERIES_UNSUBSCRIBE" and cmd.get("scope") == "LATEST_TELEMETRY":
                if self.tasks.get(task_key):
                    self.tasks[task_key].cancel()
                    del self.tasks[task_key]
                    del self.task_params[task_key]

            """
            - Entity Data
            """
            if cmd.get("type") == "ENTITY_DATA" and cmd.get("query") and cmd.get("historyCmd"):
                result = await history_telemetery(cmd, user, self.send_json)
                await self.send_json(result)

            """
            - Attributes
            """
            if (
                cmd.get("type") == "ATTRIBUTES"
                and cmd.get("entityType") == "DEVICE"
                and cmd.get("entityId")
                and cmd.get("cmdId")
            ):
                if cmd.get("scope") not in [item[0] for item in AttributeKv.ENTITY_TYPE]:
                    await self.send_json(response({}, 0, 1, "Incorrect scope!"))
                    return

                func = lambda: periodically_task(3, self, attribute_kv, cmd, user, self.send_json)

                if self.tasks.get(task_key):
                    self.tasks[task_key].cancel()
                    del self.tasks[task_key]
                    del self.task_params[task_key]

                self.task_params[task_key] = func
                self.tasks[task_key] = asyncio.create_task(func())

            if cmd.get("type") == "ATTRIBUTES_UNSUBSCRIBE" and cmd.get("entityId") and cmd.get("cmdId"):
                if self.tasks.get(task_key):
                    self.tasks[task_key].cancel()
                    del self.tasks[task_key]
                    del self.task_params[task_key]

    async def resume_tasks(self):
        for task_key, func in self.task_params.items():
            self.tasks[task_key] = asyncio.create_task(func())

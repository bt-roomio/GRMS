import asyncio

from shuttle.consumers.base import BaseConsumer
from shuttle.models import AttributeKv
from shuttle.utils.response import response

TASK_HANDLERS = {
    "TIMESERIES": "handle_latest_telemetry",
    "TIMESERIES_UNSUBSCRIBE": "unsubscribe_task",
    "ENTITY_DATA": "handle_history_telemetry",
    "ENTITY_DATA_UNSUBSCRIBE": "unsubscribe_task",
    "ATTRIBUTES": "handle_attributes",
    "ATTRIBUTES_UNSUBSCRIBE": "unsubscribe_task",
    "SCANNED_DEVICES": "handle_scanned_devices",
    "SCANNED_DEVICES_UNSUBSCRIBE": "unsubscribe_task",
    "CONTROLLER_STATUS": "handle_controller_status",
    "CONTROLLER_STATUS_UNSUBSCRIBE": "unsubscribe_task",
    "ROOM_LIST": "handle_room_list",
    "ROOM_LIST_UNSUBSCRIBE": "unsubscribe_task",
}


class ReceiverConsumer(BaseConsumer):
    async def receive_json(self, content, **kwargs):
        cmds = content.get("cmds")
        user = self.scope["user"]

        if not user.tenant_id:
            await self.send_json(response({}, 0, 1, "User does not have a tenant!"))
            return

        if not isinstance(cmds, list):
            await self.send_json(response({}, 0, 1, "`cmds` must be a list!"))
            return

        for cmd in cmds:
            handler_name = TASK_HANDLERS.get(cmd.get("type"))

            if handler_name and hasattr(self, handler_name):
                await getattr(self, handler_name)(cmd, user)
            else:
                await self.send_json(response({}, cmd.get("cmdId"), 400, "Unsupported command type"))

    async def handle_latest_telemetry(self, cmd, user):
        from shuttle.consumers.aggregations.latest_telemetry import latest_telemetry

        await self.manage_task(latest_telemetry, cmd, user)

    async def handle_history_telemetry(self, cmd, user):
        from shuttle.consumers.aggregations.ts_kv_history import history_ts_kv

        await self.manage_task(
            history_ts_kv, cmd, user, temp_index=cmd.get("historyCmd", {}).get("timeWindow", 60) * -1 + 5
        )

    async def handle_attributes(self, cmd, user):
        from shuttle.consumers.aggregations.attribute_kv import attribute_kv

        scope = cmd.get("scope")
        if scope not in [item[0] for item in AttributeKv.ENTITY_TYPE]:
            await self.send_json(response({}, 0, 1, "Incorrect scope!"))
            return
        await self.manage_task(attribute_kv, cmd, user)

    async def handle_scanned_devices(self, cmd, user):
        from shuttle.consumers.aggregations.scanned_devices import main_scanned_devices

        await self.manage_task(main_scanned_devices, cmd, self.connectors, user)

    async def handle_controller_status(self, cmd, user):
        from shuttle.consumers.aggregations.controller_status import controller_status

        await self.manage_task(controller_status, cmd, user)

    async def handle_room_list(self, cmd, user):
        from shuttle.consumers.aggregations.room_list import room_list

        await self.manage_task(room_list, cmd, user)

    async def unsubscribe_task(self, cmd, user):
        task_key = f"cmdId-{cmd.get('cmdId')}"
        if self.tasks.get(task_key):
            self.tasks[task_key].cancel()
            del self.tasks[task_key]
            del self.task_params[task_key]

    async def manage_task(self, func, cmd, *args, temp_index=None):
        task_key = f"cmdId-{cmd.get('cmdId')}"
        if self.tasks.get(task_key):
            await self.unsubscribe_task(cmd, None)

        if not func:
            await self.send_json(response({}, cmd.get("cmdId"), 400, f"Unknown function: {func}"))
            return

        def task_func():
            return self.periodically_task(func, cmd, *args, temp_index=temp_index)

        self.task_params[task_key] = task_func
        self.tasks[task_key] = asyncio.create_task(task_func())

from shuttle.consumers.base import BaseConsumer
from shuttle.consumers.utils.periodic_task import periodic_task


class ReceiverConsumer(BaseConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connectors = []

        self.TASK_HANDLERS = {
            "TIMESERIES": self.handle_latest_telemetry,
            "ENTITY_DATA": self.handle_history_telemetry,
            "ATTRIBUTES": self.handle_attributes,
            "SCANNED_DEVICES": self.handle_scanned_devices,
            "CONTROLLER_STATUS": self.handle_controller_status,
            "ROOM_LIST": self.handle_room_list,
            "GATEWAY_LIST": self.handle_gateway_list,
            "GUEST_LIST": self.handle_guest_list,
        }

    async def receive_json(self, content, **kwargs):
        for cmd in content.get("cmds", []):
            task_key = f"cmd_id-{cmd.get('cmd_id')}"

            handler = self.TASK_HANDLERS.get(cmd.get("type"))
            if handler and cmd.get("cmd_id"):
                await handler(cmd)

            if cmd.get("type").endswith("UNSUBSCRIBE") and self.tasks.get(task_key):
                await self.cancel_task(task_key)

    @periodic_task()
    async def handle_guest_list(self, cmd):
        from shuttle.consumers.aggregations.guest_list import guest_list

        return await guest_list(cmd, self.user)

    @periodic_task()
    async def handle_room_list(self, cmd):
        from shuttle.consumers.aggregations.room_list import room_list

        return await room_list(cmd, self.user)

    @periodic_task()
    async def handle_latest_telemetry(self, cmd):
        from shuttle.consumers.aggregations.latest_telemetry import latest_telemetry

        return await latest_telemetry(cmd, self.user)

    @periodic_task()
    async def handle_attributes(self, cmd):
        from shuttle.consumers.aggregations.attribute_kv import attribute_kv

        return await attribute_kv(cmd, self.user)

    @periodic_task()
    async def handle_gateway_list(self, cmd):
        from shuttle.consumers.aggregations.gateway_list import gateway_list

        return await gateway_list(cmd, self.user)

    @periodic_task()
    async def handle_scanned_devices(self, cmd):
        from shuttle.consumers.aggregations.scanned_devices import main_scanned_devices

        return await main_scanned_devices(cmd, self.connectors, self.user)

    @periodic_task()
    async def handle_controller_status(self, cmd):
        from shuttle.consumers.aggregations.controller_status import controller_status

        return await controller_status(cmd, self.user)

    @periodic_task()
    async def handle_history_telemetry(self, cmd):
        from core.utils.get_time import get_mil_sec
        from shuttle.consumers.aggregations.ts_kv_history import history_ts_kv

        res = await history_ts_kv(cmd, self.user)

        if any(list(res.get("update", {}).values())):
            last_time = cmd.get("history_cmd", {}).get("end_ts", get_mil_sec())
            cmd["history_cmd"]["start_ts"] = last_time
            return res
        return res

import asyncio

from shuttle.consumers.base import BaseConsumer
from shuttle.consumers.latest_telemetry import latest_telemetry
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
            if cmd.get("type") == "TIMESERIES" and cmd.get("scope") == "LATEST_TELEMETRY":
                self.tasks["TIMESERIES"] = asyncio.create_task(
                    periodically_task(5, latest_telemetry, cmd, user, self.send_json)
                )

            if cmd.get("type") == "TIMESERIES_UNSUBSCRIBE" and cmd.get("scope") == "LATEST_TELEMETRY":
                if self.tasks.get("TIMESERIES"):
                    self.tasks["TIMESERIES"].cancel()

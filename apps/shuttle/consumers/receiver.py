import asyncio

from shuttle.consumers.aggregations.attribute_kv import attribute_kv
from shuttle.consumers.aggregations.gateway_list import gateway_list
from shuttle.consumers.aggregations.latest_telemetry import latest_telemetry
from shuttle.consumers.aggregations.scanned_devices import main_scanned_devices
from shuttle.consumers.base import BaseConsumer
from shuttle.models import AttributeKv
from shuttle.utils.camel_to_snake import camel_to_snake
from shuttle.utils.response import response


class ReceiverConsumer(BaseConsumer):
    async def get_object_or_empty(self, queryset, *filter_args, **filter_kwargs):
        from channels.db import database_sync_to_async

        return await database_sync_to_async(queryset.filter)(*filter_args, **filter_kwargs)

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
                and cmd.get("entityId")
            ):
                if self.tasks.get(task_key):
                    self.tasks[task_key].cancel()
                    del self.tasks[task_key]
                    del self.task_params[task_key]

                def func():
                    return self.periodically_task(latest_telemetry, cmd, user)

                self.task_params[task_key] = func
                self.tasks[task_key] = asyncio.create_task(func())

            if cmd.get("type") == "TIMESERIES_UNSUBSCRIBE" and cmd.get("scope") == "LATEST_TELEMETRY":
                if self.tasks.get(task_key):
                    self.tasks[task_key].cancel()
                    del self.tasks[task_key]
                    del self.task_params[task_key]

            """
            - Attributes
            """
            if (
                cmd.get("entityType") == "DEVICE"
                and cmd.get("type") == "ATTRIBUTES"
                and cmd.get("entityId")
                and cmd.get("scope")
            ):
                if cmd.get("scope") not in [item[0] for item in AttributeKv.ENTITY_TYPE]:
                    await self.send_json(response({}, 0, 1, "Incorrect scope!"))
                    return

                #  If cmdId same remove from tasks and re-write cmd
                if self.tasks.get(task_key):
                    self.tasks[task_key].cancel()
                    del self.tasks[task_key]
                    del self.task_params[task_key]

                def func():
                    return self.periodically_task(attribute_kv, cmd, user)

                self.task_params[task_key] = func
                self.tasks[task_key] = asyncio.create_task(func())

            if cmd.get("type") == "ATTRIBUTES_UNSUBSCRIBE" and cmd.get("entityId") and cmd.get("cmdId"):
                if self.tasks.get(task_key):
                    self.tasks[task_key].cancel()
                    del self.tasks[task_key]
                    del self.task_params[task_key]
            """
            - Entity Data
            """
            # Gateway List
            if (
                cmd.get("type") == "ENTITY_DATA"
                and cmd.get("latestCmd")
                and cmd.get("query")
                and cmd.get("scope") == "gateway"
            ):
                result = response({}, cmd.get("cmdId"))

                entity_fields = cmd.get("query").get("entityFields")
                entity_fields = [camel_to_snake(i.get("key")) for i in entity_fields]

                attributes = [i.get("key") for i in cmd.get("latestCmd").get("keys") if i.get("type") == "ATTRIBUTE"]

                result["data"] = await gateway_list(entity_fields, attributes, user)
                await self.send_json(result)

            """
            Connector list
            """
            if (
                cmd.get("type") == "SCANNED_DEVICES"
                and cmd.get("entityType") == "DEVICE"
                and cmd.get("entityId")
                and cmd.get("query")
                and cmd.get("connectorName")
            ):
                # If cmdId same remove from tasks and re-write cmd
                if self.tasks.get(task_key):
                    self.tasks[task_key].cancel()
                    del self.tasks[task_key]
                    del self.task_params[task_key]

                def func():
                    return self.periodically_task(main_scanned_devices, cmd, self.connectors, user)

                self.task_params[task_key] = func
                self.tasks[task_key] = asyncio.create_task(func())

            if (
                cmd.get("type") == "SCANNED_DEVICES_UNSUBSCRIBE"
                and cmd.get("entityType") == "DEVICE"
                and cmd.get("entityId")
                and cmd.get("connectorName")
            ):
                if self.tasks.get(task_key):
                    self.tasks[task_key].cancel()
                    del self.tasks[task_key]
                    del self.task_params[task_key]

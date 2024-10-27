import asyncio

from shuttle.consumers.aggregations.attribute_kv import attribute_kv
from shuttle.consumers.aggregations.connectors import make_connectors
from shuttle.consumers.aggregations.gateway_list import gateway_list
from shuttle.consumers.aggregations.latest_telemetry import latest_telemetry
from shuttle.consumers.base import BaseConsumer
from shuttle.models import AttributeKv
from shuttle.utils.camel_to_snake import camel_to_snake
from shuttle.utils.response import response


class ReceiverConsumer(BaseConsumer):
    async def get_object_or_404_ws(self, queryset, *filter_args, **filter_kwargs):
        from django.http import Http404
        from channels.db import database_sync_to_async
        from rest_framework.generics import get_object_or_404

        try:
            return await database_sync_to_async(get_object_or_404)(queryset, *filter_args, **filter_kwargs)
        except Http404 as err:
            await self.send_json(response({}, 0, 1, str(err)))

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
                    return self.periodically_task(attribute_kv, cmd)

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
            if cmd.get("type") == "ENTITY_DATA" and cmd.get("latestCmd") and cmd.get("query"):
                result = response({}, cmd.get("cmdId"))

                entity_fields = cmd.get("query").get("entityFields")
                entity_fields = [camel_to_snake(i.get("key")) for i in entity_fields]

                attributes = [i.get("key") for i in cmd.get("latestCmd").get("keys") if i.get("type") == "ATTRIBUTE"]

                result["data"] = await gateway_list(entity_fields, attributes)
                await self.send_json(result)

            if cmd.get("type") == "ENTITY_DATA" and cmd.get("query") and cmd.get("historyCmd"):
                from shuttle.consumers.aggregations.ts_kv_history import history_telemetry

                result = await history_telemetry(cmd)
                await self.send_json(result)

            """
            - Entity Data
            """
            if (
                cmd.get("type") == "ENTITY_DATA"
                and cmd.get("entityType") == "DEVICE"
                and cmd.get("query")
                and cmd.get("entityId")
                and cmd.get("connectorName")
            ):
                if not self.connectors:
                    print("not connectors")
                    self.connectors = make_connectors()
                query = cmd.get("query")
                page = query.get("page") or 1
                page_size = query.get("pageSize")
                offset = (page - 1) * page_size
                limit = offset + page_size
                await self.send_json(self.connectors[offset:limit])

            """
            Connector list
            """
            if (
                cmd.get("type") == "SCANNED_DEVICES"
                and cmd.get("entityType") == "DEVICE"
                and cmd.get("entityId")
                and cmd.get("connectorName")
            ):
                from main.models import Device

                device = await self.get_object_or_404_ws(Device, id=cmd.get("entityId"), additional_info__gateway=True)
                attrs = await self.get_object_or_404_ws(
                    AttributeKv,
                    entity=device,
                    attribute_type=AttributeKv.SHARED_SCOPE,
                    attribute_key=cmd.get("connectorName"),
                )
                configuration_json = attrs and attrs.json_v and attrs.json_v.get("configurationJson") or {}
                devices = configuration_json.get("devices") or {}
                address_maps = {
                    i.get("addressMapId"): i.get("addressMapName") for i in configuration_json.get("addressMaps")
                }
                temp_devices = [i.get("macAddress") for i in devices if i.get("tempDevice")]
                not_temp_devices = list(filter(lambda x: not x.get("tempDevice"), devices))
                result = []
                from shuttle.consumers.aggregations.scanned_devices import get_scanned_devices
                from shuttle.consumers.aggregations.scanned_devices import get_gateway_attrs

                await get_scanned_devices(temp_devices, not_temp_devices, address_maps, result)
                await get_gateway_attrs(not_temp_devices, address_maps, result)
                await self.send_json({"devices": result})

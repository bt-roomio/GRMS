from typing import cast

from djangochannelsrestframework.mixins import action

from main.models import Device
from main.querysets.device import DeviceQuerySet
from main.serializers.device import DeviceFilterParams, DeviceSerializer
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class DevicesListConsumer(BaseGenericAsyncAPIConsumer):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer

    def get_queryset(self, **kwargs):
        query = cast(DeviceQuerySet, super().get_queryset(**kwargs))
        params = DeviceFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.list(
            tenant=self.tenant_id,
            status=params.get("status"),
            search_field=params.get("search_field"),
            search_value=params.get("search_value"),
            sort_by=params.get("sort_by"),
        )
        return query

    async def get_latest_activity(self, message, **kwargs):
        for update in message.get("updates", []) or []:
            await self.get_latest_activity({"update": update}, **kwargs)
            continue

        for request_id, params in self.subscribers.items():
            await self.send_list_paginated(params.get("action"), params.get("query_params"), request_id)

    @action()
    async def list_subscribe(self, request_id, action, query_params, **kwargs):
        await self.send_list_paginated(action, query_params, request_id)

        await self.add_group(f"device_{self.tenant_id}")
        self.subscribers[request_id] = {"query_params": query_params, "action": action}

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        await self.remove_group(f"device_{self.tenant_id}")
        self.subscribers.pop(request_id, None)

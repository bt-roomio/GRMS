from access_manager.models import NeedSyncDevice
from access_manager.serializers.need_sync import NeedSyncDeviceFilterParams, NeedSyncDeviceSerializer
from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import action

from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class NeedSyncConsumer(BaseGenericAsyncAPIConsumer):
    queryset = NeedSyncDevice.objects.all()
    serializer_class = NeedSyncDeviceSerializer

    async def accept(self, *args, **kwargs):
        self.subscribers = {}
        await super().accept(*args, **kwargs)

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        params = NeedSyncDeviceFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.list(sort_by=params.get("sort_by"))
        return query

    async def get_list_activity(self, message, **kwargs):
        for request_id, params in self.subscribers.items():
            query_params = params.get("query_params")
            data = await sync_to_async(self.get_data_paginated)(query_params=query_params, **kwargs)
            await self.reply(data=data, action="list_subscribe", request_id=request_id)

    @action()
    async def list_subscribe(self, **kwargs):
        await self.send_list_paginated(**kwargs)
        await self.add_group("need_sync")
        self.subscribers[kwargs.get("request_id")] = kwargs

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)

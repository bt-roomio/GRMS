from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import ListModelMixin, action
from djangochannelsrestframework.observer import model_observer

from main.models import Room
from main.serializers.room import RoomFilterParams, RoomSerializer
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class RoomConsumer(ListModelMixin, BaseGenericAsyncAPIConsumer):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    async def accept(self, *args, **kwargs):
        self.request_ids = {}
        self.scope["user"] = await sync_to_async(self.get_user)()
        await super().accept(*args, **kwargs)

    @action()
    def list(self, **kwargs):  # pyright: ignore
        res = self.get_data_paginated(**kwargs)
        return res, 200

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        user = self.scope["user"]
        params = RoomFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.list(tenant=user.get("tenant_id"), sort_by=params.get("sort_by"))  # pyright: ignore
        return query

    @model_observer(Room, serializer_class=RoomSerializer)
    async def get_latest_activity(self, message, action, **kwargs):
        for request_id, _ in self.request_ids.items():
            tenant_id = self.scope["user"].get("tenant_id")
            if str(tenant_id) == message.get("tenant"):
                await self.reply(data=message, action=action, request_id=request_id)

    @action()
    async def subscribe(self, request_id, query_params, **kwargs):
        await self.get_latest_activity.subscribe(request_id=request_id, **kwargs)
        self.request_ids[request_id] = query_params

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        await self.get_latest_activity.unsubscribe(request_id=request_id, **kwargs)

    @model_observer(Room, serializer_class=RoomSerializer)
    async def get_list_activity(self, message, action, **kwargs):
        for request_id, params in self.request_ids.items():
            tenant_id = self.scope["user"].get("tenant_id")
            if str(tenant_id) == message.get("tenant"):
                data = await sync_to_async(self.get_data_paginated)(query_params=params, **kwargs)
                if any([message.get("id") == i["id"] for i in data.get("results", [])]):
                    await self.reply(data=data, action=action, request_id=request_id)

    @action()
    async def list_subscribe(self, request_id, action, query_params, **kwargs):
        await self.send_list_paginated(action, query_params, request_id, **kwargs)
        await self.get_list_activity.subscribe(request_id=request_id, **kwargs)
        self.request_ids[request_id] = query_params

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        await self.get_list_activity.unsubscribe(request_id=request_id, **kwargs)

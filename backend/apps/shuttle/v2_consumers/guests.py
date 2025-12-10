from asgiref.sync import sync_to_async
from djangochannelsrestframework.observer.generics import action

from main.models import Guest
from main.serializers.guest import GuestFilterParams, GuestSerializer
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class GuestConsumer(BaseGenericAsyncAPIConsumer):
    queryset = Guest.objects.all()
    serializer_class = GuestSerializer

    @action()
    def list(self, **kwargs):  # pyright: ignore
        res = self.get_data_paginated(**kwargs)
        return res, 200

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        params = GuestFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.list(  # pyright: ignore
            tenant_id=self.tenant_id, room=params.get("room"), sort_by=params.get("sort_by", [])
        )
        return query

    async def get_activity(self, message, **kwargs):
        update = message.get("update")
        for request_id, params in self.subscribers.items():
            room = str(params.get("room"))
            action = params.get("action")
            if room == update.get("room"):
                if action == "list_subscribe":
                    data = await sync_to_async(self.get_data_paginated)(query_params=params, **kwargs)
                    await self.reply(data=data, action="list_subscribe", request_id=request_id)
                elif action == "subscribe":
                    await self.reply(data=update, action="subscribe", request_id=request_id)

    @action()
    async def subscribe(self, request_id, query_params, **kwargs):
        await self.add_group(f"guests_{query_params.get('room')}")
        self.subscribers[request_id] = {**query_params, "action": "subscribe"}

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        await self.remove_group(f"guests_{self.subscribers[request_id].get('room')}")
        self.subscribers.pop(request_id, None)

    @action()
    async def list_subscribe(self, request_id, action, query_params, **kwargs):
        await self.send_list_paginated(action, query_params, request_id, **kwargs)
        await self.add_group(f"guests_{query_params.get('room')}")
        self.subscribers[request_id] = {**query_params, "action": action}

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        await self.remove_group(f"guests_{self.subscribers[request_id].get('room')}")
        self.subscribers.pop(request_id, None)

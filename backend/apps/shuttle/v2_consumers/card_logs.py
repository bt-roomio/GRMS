from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import action

from access_manager.models import CardLog
from access_manager.serializers.card_log import CardLogSerializer, CardLogFilterParams
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class CardLogConsumer(BaseGenericAsyncAPIConsumer):
    queryset = CardLog.objects.all()
    serializer_class = CardLogSerializer

    async def accept(self, *args, **kwargs):
        self.subscribers = {}
        await super().accept(*args, **kwargs)

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        params = CardLogFilterParams.check(data=kwargs.get("query_params", {}))

        user = self.scope["user"]
        tenant=user.get("tenant_id")

        query = query.list(
            filters=params.get("filters", {}),
            sort_by=params.get("sort_by", ["-event_ts"]),
            room_ids=params.get("room_ids", []),
            public_space_ids=params.get("public_space_ids", []),
            room_id=params.get("room"),
            public_space_id=params.get("public_space"),
            user_id=params.get("user"),
            card_num=params.get("card_num"),
            tenant=tenant
        )

        return query

    async def get_list_activity(self, message, **kwargs):
        for request_id, params in self.subscribers.items():
            query_params = params.get("query_params")
            data = await sync_to_async(self.get_data_paginated)(query_params=query_params, **kwargs)
            await self.reply(data=data, action="list_subscribe", request_id=request_id)

    @action()
    async def list_subscribe(self, **kwargs):
        await self.send_list_paginated(**kwargs)
        await self.add_group("card_logs")
        self.subscribers[kwargs.get("request_id")] = kwargs

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)

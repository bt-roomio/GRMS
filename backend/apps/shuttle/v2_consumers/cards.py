from djangochannelsrestframework.observer.generics import ObserverModelInstanceMixin, action
from djangochannelsrestframework.mixins import ListModelMixin

from asgiref.sync import sync_to_async

from access_manager.models import Card
from shuttle.serializers.cards import CardSerializer, CardFilterParams
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class CardConsumer(ListModelMixin, ObserverModelInstanceMixin, BaseGenericAsyncAPIConsumer):
    queryset = Card.objects.all()
    serializer_class = CardSerializer

    async def accept(self, *args, **kwargs):
        self.subscribers = {}
        await super().accept(*args, **kwargs)

    @action()
    def list(self, **kwargs):  # pyright: ignore
        res = self.get_data_paginated(**kwargs)
        return res, 200

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        user = self.scope["user"]
        params = CardFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.list(  # pyright: ignore
            tenant_id=user.get("tenant_id"),
            sort_by=params.get("sort_by", []),
            search_field="number",
            search_value=params.get("search_value", None),
        )
        return query

    async def get_list_activity(self, action, **kwargs):
        for request_id, params in self.subscribers.items():
            data = await sync_to_async(self.get_data_paginated)(query_params=params, **kwargs)
            await self.reply(data=data, action=action, request_id=request_id)

    @action()
    async def list_subscribe(self, **kwargs):
        await self.send_list_paginated(**kwargs)
        await self.add_group("cards")
        self.subscribers[kwargs.get("request_id")] = kwargs.get("query_params")

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        await self.get_list_activity.unsubscribe(request_id=request_id, **kwargs)

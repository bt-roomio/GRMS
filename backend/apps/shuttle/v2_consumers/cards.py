from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import ListModelMixin
from djangochannelsrestframework.observer.generics import ObserverModelInstanceMixin, action

from access_manager.models import Card
from shuttle.serializers.cards import CardFilterParams, CardSerializer
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class CardConsumer(ListModelMixin, ObserverModelInstanceMixin, BaseGenericAsyncAPIConsumer):
    queryset = Card.objects.filter(is_active=True)
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
        params = CardFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.list(  # ty: ignore
            tenant_id=self.tenant_id,
            sort_by=params.get("sort_by", []),
            search_field="number",
            search_value=params.get("search_value", None),
            filters=params.get("filters", {}),
            is_pwd=params.get("is_pwd"),
        )
        return query

    async def get_list_activity(self, message, **kwargs):
        self.request_refresh(self.refresh_lists)

    async def refresh_lists(self):
        for request_id, params in list(self.subscribers.items()):
            data = await sync_to_async(self.get_data_paginated)(query_params=params)
            await self.reply(data=data, action="list_subscribe", request_id=request_id)

    @action()
    async def list_subscribe(self, **kwargs):
        await self.send_list_paginated(**kwargs)
        await self.add_group(f"cards_{self.tenant_id}")
        self.subscribers[kwargs.get("request_id")] = kwargs.get("query_params")

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)
        if not self.subscribers:
            await self.remove_group(f"cards_{self.tenant_id}")

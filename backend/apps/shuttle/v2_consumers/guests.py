from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import ListModelMixin
from djangochannelsrestframework.observer import model_observer
from djangochannelsrestframework.observer.generics import ObserverModelInstanceMixin, action

from main.models import Guest
from main.serializers.guest import GuestFilterParams, GuestSerializer
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class GuestConsumer(ListModelMixin, ObserverModelInstanceMixin, BaseGenericAsyncAPIConsumer):
    queryset = Guest.objects.all()
    serializer_class = GuestSerializer

    async def accept(self, *args, **kwargs):
        self.request_ids = {}
        await super().accept(*args, **kwargs)

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        user = self.scope["user"]
        params = GuestFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.list(  # pyright: ignore
            tenant_id=user.tenant_id, room=params.get("room"), sort_by=params.get("sort_by", [])
        )
        query = self.pagination(query, params.get("page", 1), params.get("size", 15))
        return query

    @model_observer(Guest, serializer_class=GuestSerializer)
    async def get_latest_activity(self, message, action, **kwargs):
        for request_id, params in self.request_ids.items():
            room = params.get("room")
            if room == message.get("room"):
                await self.reply(data=message, action=action, request_id=request_id)

    @action()
    async def subscribe(self, request_id, query_params, **kwargs):
        await self.get_latest_activity.subscribe(request_id=request_id, **kwargs)
        self.request_ids[request_id] = query_params

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        await self.get_latest_activity.unsubscribe(request_id=request_id, **kwargs)

    @model_observer(Guest, serializer_class=GuestSerializer)
    async def get_list_activity(self, message, action, **kwargs):
        for request_id, params in self.request_ids.items():
            room = params.get("room")
            if room == message.get("room"):
                data = await sync_to_async(self.get_data)(query_params=params, **kwargs)
                await self.reply(data=data, action=action, request_id=request_id)

    @action()
    async def list_subscribe(self, request_id, action, query_params, **kwargs):
        await self.send_list(action, query_params, request_id, **kwargs)
        await self.get_list_activity.subscribe(request_id=request_id, **kwargs)
        self.request_ids[request_id] = query_params

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        await self.get_list_activity.unsubscribe(request_id=request_id, **kwargs)

from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import ListModelMixin, action
from djangochannelsrestframework.observer import model_observer

from shuttle.models import TsKvLatest
from shuttle.serializers.ts_kv_latest import SimpleTsKvLatestSerializer, TsKvLatestFilterParams, TsKvLatestSerializer
from shuttle.utils.get_non_null_field import get_non_null_column
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class TsKvLatestConsumer(ListModelMixin, BaseGenericAsyncAPIConsumer):
    queryset = TsKvLatest.objects.all()
    serializer_class = TsKvLatestSerializer

    async def accept(self, *args, **kwargs):
        self.request_ids = {}
        await super().accept(*args, **kwargs)

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        user = self.scope["user"]
        params = TsKvLatestFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.get_ts_kv_latest(  # pyright: ignore
            entity=params.get("device"), tenant=user.tenant, sort_by=params.get("sort_by", [])
        )
        query = self.pagination(query, params.get("page", 1), params.get("size", 25))
        return query

    @model_observer(TsKvLatest, serializer_class=SimpleTsKvLatestSerializer)
    async def get_latest_activity(self, message, action, **kwargs):
        for request_id, params in self.request_ids.items():
            device = params.get("device")
            if device == message.get("entity"):
                _, value = get_non_null_column(message)
                message = {
                    "key_name": message.get("key"),
                    "ts": message.get("ts"),
                    "value": value,
                }
                await self.reply(data=message, action=action, request_id=request_id)

    @action()
    async def subscribe(self, request_id, query_params, **kwargs):
        await self.get_latest_activity.subscribe(request_id=request_id, **kwargs)
        self.request_ids[request_id] = query_params

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        self.request_ids.pop(request_id, None)

    @model_observer(TsKvLatest, serializer_class=SimpleTsKvLatestSerializer)
    async def get_list_activity(self, message, action, **kwargs):
        for request_id, params in self.request_ids.items():
            device = params.get("device")
            if device == message.get("entity"):
                data = await sync_to_async(self.get_data)(query_params=params, **kwargs)
                if any([message.get("key") == i["key_name"] for i in data]):
                    await self.reply(data=data, action=action, request_id=request_id)

    @action()
    async def list_subscribe(self, request_id, action, query_params, **kwargs):
        await self.send_list(action, query_params, request_id, **kwargs)
        await self.get_list_activity.subscribe(request_id=request_id, **kwargs)
        self.request_ids[request_id] = query_params

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        await self.get_list_activity.unsubscribe(request_id=request_id, **kwargs)

from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import ListModelMixin, action

from shuttle.models import AttributeKv
from shuttle.serializers.attributes import AttributeFilterParams, AttributeSerializer
from shuttle.utils.get_non_null_field import get_non_null_column
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class AttributeConsumer(ListModelMixin, BaseGenericAsyncAPIConsumer):
    queryset = AttributeKv.objects.all()
    serializer_class = AttributeSerializer

    async def accept(self, *args, **kwargs):
        self.request_ids = {}
        await super().accept(*args, **kwargs)

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        params = AttributeFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.get_attributes(  # pyright: ignore
            device=params.get("device"),
            scope=params.get("scope"),
            sort_by=params.get("sort_by", []),
        )
        query = self.pagination(query, params.get("page", 1), params.get("size", 25))
        return query

    async def get_latest_activity(self, message, **kwargs):
        for request_id, params in self.request_ids.items():
            device = params.get("query_params").get("device")
            scope = params.get("query_params").get("scope")
            action = params.get("action")

            if device == message.get("entity") and action == "list_subscribe" and scope == message.get("scope"):
                data = await sync_to_async(self.get_data)(query_params=params.get("query_params"), **kwargs)
                if any([message.get("key_name") == i["key_name"] for i in data]):
                    await self.reply(data=data, action="list_subscribe", request_id=request_id)

            elif device == message.get("entity") and action == "subscribe" and scope == message.get("scope"):
                _, value = get_non_null_column(message)
                message = {
                    "key_name": message.get("key_name"),
                    "last_update_ts": message.get("last_update_ts"),
                    "value": value,
                }
                await self.reply(data=message, action="subscribe", request_id=request_id)

    @action()
    async def subscribe(self, request_id, action, query_params, **kwargs):
        if self.channel_layer is not None:
            await self.channel_layer.group_add("attribute_kv_updates", self.channel_name)
            self.request_ids[request_id] = {"query_params": query_params, "action": action}

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        self.request_ids.pop(request_id, None)

    @action()
    async def list_subscribe(self, request_id, action, query_params, **kwargs):
        await self.send_list(action, query_params, request_id, **kwargs)
        if self.channel_layer is not None:
            await self.channel_layer.group_add("attribute_kv_updates", self.channel_name)
            self.request_ids[request_id] = {"query_params": query_params, "action": action}

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        self.request_ids.pop(request_id, None)

from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import ListModelMixin

from shuttle.models import AttributeKv
from shuttle.serializers.attributes import AttributeFilterParams, AttributeSerializer
from shuttle.utils.get_non_null_field import get_non_null_column
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer
from shuttle.v2_consumers.generics.list_subscribe import ListSubscribeMixin
from shuttle.v2_consumers.generics.subscribe import SubscribeMixin


class AttributeConsumer(ListModelMixin, BaseGenericAsyncAPIConsumer, SubscribeMixin, ListSubscribeMixin):
    queryset = AttributeKv.objects.all()
    serializer_class = AttributeSerializer
    group_name = "attribute_kv_updates"

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

    async def get_latest_activity(self, message):
        updates = message.get("updates", []) or []
        for update in updates:
            await self.handle_ts_kv_activity(update)
        if not updates:
            await self.handle_ts_kv_activity(message.get("update"))

    async def handle_ts_kv_activity(self, payload):
        for request_id, params in self.subscribers.items():
            device = params.get("query_params").get("device")
            scope = params.get("query_params").get("scope")
            action = params.get("action")

            if device == payload.get("entity") and action == "list_subscribe" and scope == payload.get("scope"):
                data = await sync_to_async(self.get_data)(query_params=params.get("query_params"))
                if any([payload.get("key_name") == i["key_name"] for i in data]):
                    await self.reply(data=data, action="list_subscribe", request_id=request_id)

            elif device == payload.get("entity") and action == "subscribe" and scope == payload.get("scope"):
                _, value = get_non_null_column(payload)
                payload = {
                    "key_name": payload.get("key_name"),
                    "last_update_ts": payload.get("last_update_ts"),
                    "value": value,
                }
                await self.reply(data=payload, action="subscribe", request_id=request_id)

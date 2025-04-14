from asgiref.sync import sync_to_async
from djangochannelsrestframework.observer.generics import action

from shuttle.models import TsKv
from shuttle.serializers.ts_kv import TagLogsFilterParams, TsKvSerializer
from shuttle.utils.get_non_null_field import get_non_null_column
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class TagLogsConsumer(BaseGenericAsyncAPIConsumer):
    queryset = TsKv.objects.all()
    serializer_class = TsKvSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subscribers = {}
        self.last_value = None
        self.count = 0

    def get_data_paginated(self, query_params, **kwargs):
        queryset = self.get_queryset(query_params=query_params)
        queryset = self.pagination(queryset, query_params.get("page", 1), query_params.get("size", 15))
        serializer = self.get_serializer(instance=queryset, many=True, action_kwargs=kwargs)
        return {"results": serializer.data, "count": self.count}

    async def send_list_paginated(self, action, query_params, request_id, **kwargs):
        data = await sync_to_async(self.get_data_paginated)(query_params=query_params, **kwargs)
        self.last_value = data.get("results", []) and data.get("results", [])[0].get("value")
        await self.reply(data=data, action=action, request_id=request_id)

    def get_queryset(self, **kwargs):  # pyright: ignore
        query = super().get_queryset(**kwargs)
        params = TagLogsFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.tag_logs(  # pyright: ignore
            entity=params.get("device"),
            keys=params.get("keys"),
            start_ts=params.get("start_ts"),
            sort_by=params.get("sort_by", []),
        )
        self.count = query.count()
        return query

    async def get_latest_activity(self, message, **kwargs):
        entity = message.pop("entity")
        key = message.pop("key")
        _, value = get_non_null_column(message)
        del message["ts"]
        del message["type"]

        for request_id, params in self.subscribers.items():
            query_params = params.get("query_params")
            if query_params.get("device") == entity and query_params.get("key") == key and value != self.last_value:
                # Checking entity and key and last value is equal to new_value
                data = await sync_to_async(self.get_data_paginated)(query_params=query_params, **kwargs)
                await self.reply(data=data, action="subscribe", request_id=request_id)

    @action()
    async def list_subscribe(self, **kwargs):
        await self.send_list_paginated(**kwargs)
        await self.add_group("tskv_updates")
        self.subscribers[kwargs.get("request_id")] = kwargs

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)

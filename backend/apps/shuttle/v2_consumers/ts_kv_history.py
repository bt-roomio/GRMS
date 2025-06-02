from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import action

from core.utils.date import convert_datetime
from main.models import Device
from shuttle.models import TsKv
from shuttle.serializers.ts_kv_history import TsKvHistoryFilterParams, TsKvHistorySerializer
from shuttle.utils.get_non_null_field import get_non_null_column
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class TsKvHistoryConsumer(BaseGenericAsyncAPIConsumer):
    queryset = TsKv.objects.all()
    serializer_class = TsKvHistorySerializer

    async def accept(self, *args, **kwargs):
        self.subscribers = {}
        await super().accept(*args, **kwargs)

    def get_data_paginated(self, query_params, **kwargs):
        queryset = self.get_queryset(query_params=query_params)
        for key in queryset:
            serializer = self.get_serializer(instance=queryset[key], many=True, action_kwargs=kwargs)
            queryset[key] = serializer.data
        return queryset

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        params = TsKvHistoryFilterParams.check(data=kwargs.get("query_params", {}))
        params["device"] = (
            Device.objects.filter(room__id=params.get("room"), is_active=True).first()
            if params.get("room")
            else params.get("device")
        )
        query = query.by_device(entity=params.get("device")).get_history_v2(  # pyright: ignore
            keys=params.get("keys"),
            start_ts=convert_datetime(params.get("start_ts")) if params.get("start_ts") else None,
            interval=params.get("interval"),
            agg=params.get("agg"),
            limit=params.get("limit"),
            sort_by=params.get("sort_by"),
            auto_fill=params.get("auto_fill"),
        )
        return query

    async def get_latest_ts_kv_activity(self, message, **kwargs):
        entity = message.pop("entity")
        key = message.pop("key")
        _, value = get_non_null_column(message)
        del message["ts"]
        del message["type"]

        for request_id, params in self.subscribers.items():
            query_params = params.get("query_params")
            if query_params.get("device") == entity and key in query_params.get("keys", []):
                data = await sync_to_async(self.get_data_paginated)(query_params=query_params, **kwargs)
                await self.reply(data=data, action="subscribe", request_id=request_id)
                self.last_value = value

    @action()
    async def list_subscribe(self, **kwargs):
        await self.send_list_paginated(**kwargs)
        await self.add_group("tskv_updates")
        self.subscribers[kwargs.get("request_id")] = kwargs

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)

from djangochannelsrestframework.mixins import action

from core.utils.date import convert_datetime
from main.models import Device
from shuttle.models import TsKv
from shuttle.serializers.ts_kv_history import TsKvHistoryFilterParams, TsKvHistorySerializer
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class TsKvHistoryConsumer(BaseGenericAsyncAPIConsumer):
    queryset = TsKv.objects.all()
    serializer_class = TsKvHistorySerializer

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

    async def ts_kv_activity(self, message):
        updates = message.get("updates", []) or []
        for update in updates:
            await self.handle_ts_kv_activity(update)
        if not updates:
            await self.handle_ts_kv_activity(message.get("update"))

    async def handle_ts_kv_activity(self, payload):
        if not payload or isinstance(payload, dict) or "entity" not in payload:
            return
        entity = payload.pop("entity")
        key = payload.pop("key")

        for request_id, params in self.subscribers.items():
            qp = params.get("query_params")
            if qp.get("device") == entity and key in qp.get("keys", []):
                await self.send_list_paginated(params.get("action"), qp, request_id)

    @action()
    async def list_subscribe(self, request_id, query_params, action):
        res = await self.send_list_paginated(action, query_params, request_id)
        await self.add_group(f"tskv_updates_{query_params.get('device')}")
        self.subscribers[request_id] = {"query_params": query_params, "action": action, "response": res}

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)

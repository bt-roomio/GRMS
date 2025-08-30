from djangochannelsrestframework.observer.generics import action

from shuttle.models import TsKv
from shuttle.serializers.ts_kv import TagLogsFilterParams, TsKvSerializer
from shuttle.utils.get_non_null_field import get_non_null_column
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class TagLogsConsumer(BaseGenericAsyncAPIConsumer):
    queryset = TsKv.objects.all()
    serializer_class = TsKvSerializer

    def get_queryset(self, **kwargs):  # pyright: ignore
        query = super().get_queryset(**kwargs)
        params = TagLogsFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.by_tenant(self.tenant_id).tag_logs(  # pyright: ignore
            entity=params.get("device"),
            keys=params.get("keys"),
            all_tags=params.get("all_tags"),
            start_ts=params.get("start_ts"),
            end_ts=params.get("end_ts"),
            sort_by=params.get("sort_by", []),
        )
        return query

    async def ts_kv_activity(self, message):
        updates = message.get("updates", []) or []
        for update in updates:
            await self.handle_ts_kv_activity(update)
        if not updates:
            await self.handle_ts_kv_activity(message.get("update"))

    async def handle_ts_kv_activity(self, payload):
        entity = payload.get("entity")
        key = payload.get("key")
        _, value = get_non_null_column(payload)

        for request_id, params in self.subscribers.items():
            qp = params.get("query_params")
            res = params.get("response").get("results", [])
            if qp.get("device") == entity and (qp.get("all_tags") or key in qp.get("keys", [])):
                last_value_same = self.find_last_value(res, key, value)
                if not last_value_same:
                    res.insert(0, {"ts": payload.get("ts"), "key_name": key, "value": value})
                    params["response"]["results"] = res
                    params["response"]["count"] += 1
                    await self.reply(data=params["response"], action=params.get("action"), request_id=request_id)

    def find_last_value(self, results, key, value):
        for result in results:
            if result.get("key_name") == key:
                return result.get("value") == value

    @action()
    async def list_subscribe(self, request_id, query_params, action):
        res = await self.send_list_paginated(action, query_params, request_id)
        await self.add_group(f"tskv_updates_{query_params.get("device")}")
        self.subscribers[request_id] = {"query_params": query_params, "action": action, "response": res}

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)

from django.utils import timezone
from djangochannelsrestframework.mixins import action

from shuttle.models import TsKv
from shuttle.serializers.ts_kv import GatewayLogsFilterParams, GatewayLogsSerializer
from shuttle.utils.get_non_null_field import get_non_null_column
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


def convert_datetime(date: str):
    from django.utils.dateparse import parse_datetime
    from django.utils.timezone import make_aware

    dt = parse_datetime(date)
    if dt and not timezone.is_aware(dt):
        dt = make_aware(dt)
    return dt


class GatewayLogsConsumer(BaseGenericAsyncAPIConsumer):
    queryset = TsKv.objects.all()
    serializer_class = GatewayLogsSerializer

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        params = GatewayLogsFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.by_tenant(tenant=self.tenant_id).gateway_logs(  # pyright: ignore
            entity=params.get("device"),
            key=params.get("key"),
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
        entity, key = payload.get("entity"), payload.get("key")
        for request_id, params in self.subscribers.items():
            qp = params.get("query_params")
            _, value = get_non_null_column(payload)
            data = {
                "key_name": payload.get("key"),
                "ts": payload.get("ts"),
                "value": value,
            }
            if qp.get("device") == entity and key == qp.get("key"):
                await self.reply(params.get("action"), data, request_id=request_id)

    @action()
    async def list(self, request_id, action, query_params):
        await self.send_list_paginated(action, query_params, request_id)

    @action()
    async def subscribe(self, request_id, action, query_params):
        await self.add_group(f"tskv_updates_{query_params.get('device')}")
        self.subscribers[request_id] = {"query_params": query_params, "action": action}

    @action()
    async def list_unsubscribe(self, request_id):
        self.subscribers.pop(request_id, None)

from django.utils import timezone
from djangochannelsrestframework.mixins import action

from core.utils.date import unix_to_datetime
from shuttle.models import TsKv
from shuttle.serializers.ts_kv import GatewayLogsFilterParams, GatewayLogsSerializer
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
        query = (
            query.by_device(entity=params.get("device"))  # pyright: ignore
            .by_tenant(tenant=self.tenant_id)
            .gateway_logs(
                key=params.get("key"),
                start_ts=params.get("start_ts"),
                end_ts=params.get("end_ts"),
                sort_by=params.get("sort_by", []),
            )
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
            query_params = params.get("query_params")

            # Checking for payload ts
            end_ts = convert_datetime(query_params.get("end_ts") or "")
            ts = payload.get("ts")
            if ts and isinstance(ts, int):
                ts = unix_to_datetime(ts)
            elif ts and isinstance(ts, str):
                ts = convert_datetime(ts)
            if end_ts and ts and end_ts < ts:
                return

            if query_params.get("device") == entity and key == query_params.get("key"):
                await self.send_list_paginated(params.get("action"), query_params, request_id)

    @action()
    async def list_subscribe(self, request_id, action, query_params):
        await self.send_list_paginated(action, query_params, request_id)
        await self.add_group(f"tskv_updates_{query_params.get('device')}")
        self.subscribers[request_id] = {"query_params": query_params, "action": action}

    @action()
    async def list_unsubscribe(self, request_id):
        self.subscribers.pop(request_id, None)

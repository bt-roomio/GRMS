import logging

from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import action

from core.utils.date import convert_datetime
from shuttle.models import TsKv
from shuttle.serializers.ts_kv_history import TenantRoomAvgParams, TsKvHistorySerializer
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer

logger = logging.getLogger(__name__)


class TsKvTenantHistoryConsumer(BaseGenericAsyncAPIConsumer):
    queryset = TsKv.objects.all()
    serializer_class = TsKvHistorySerializer

    def get_data_paginated(self, query_params, **kwargs):
        data = self.get_queryset(query_params=query_params)
        for key in data:
            data[key] = self.get_serializer(instance=data[key], many=True, action_kwargs=kwargs).data
        return data

    def get_queryset(self, **kwargs):
        p = TenantRoomAvgParams.check(kwargs.get("query_params", {}))
        tenant_id = self.tenant_id
        return TsKv.objects.tenant_avg_history(
            tenant=tenant_id,
            keys=p.get("keys", []),
            start_ts=convert_datetime(p.get("start_ts")) if p.get("start_ts") else None,
            end_ts=convert_datetime(p.get("end_ts")) if p.get("end_ts") else None,
            interval=p.get("interval"),
            limit=p.get("limit"),
        )

    async def ts_kv_activity(self, message):
        for request_id, sub in list(self.subscribers.items()):
            try:
                query_params = sub.get("query_params", {}) or {}
                action = sub.get("action")
                previous = sub.get("response")

                fresh = await sync_to_async(self.get_data_paginated)(query_params=query_params)

                if fresh != previous:
                    self.subscribers[request_id]["response"] = fresh
                    await self.reply(data=fresh, action=action, request_id=request_id)

            except Exception as exc:
                logger.warning(f"ts_kv_activity error for {request_id}: {exc}")
                continue

    @action()
    async def list_subscribe(self, request_id, query_params, action):
        res = await self.send_list_paginated(action, query_params, request_id)
        await self.add_group(f"tskv_updates_tenant_{self.tenant_id}")
        self.subscribers[request_id] = {"query_params": query_params, "action": action, "response": res}

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)

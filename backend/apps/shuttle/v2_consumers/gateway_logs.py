from djangochannelsrestframework.mixins import ListModelMixin, action

from core.utils.get_time import get_mil_sec
from shuttle.models import TsKv
from shuttle.serializers.ts_kv import GatewayLogsFilterParams, GatewayLogsSerializer
from shuttle.utils.get_non_null_field import get_non_null_column
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class GatewayLogsConsumer(ListModelMixin, BaseGenericAsyncAPIConsumer):
    queryset = TsKv.objects.all()
    serializer_class = GatewayLogsSerializer

    async def accept(self, *args, **kwargs):
        self.request_ids = {}
        await super().accept(*args, **kwargs)

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        user = self.scope["user"]
        params = GatewayLogsFilterParams.check(data=kwargs.get("query_params", {}))
        query = (
            query.by_device(entity=params.get("device"))  # pyright: ignore
            .by_tenant(tenant=user.get("tenant_id"))
            .gateway_logs(
                key=params.get("key"),
                start_ts=params.get("start_ts"),
                end_ts=params.get("end_ts", get_mil_sec()),
                sort_by=params.get("sort_by", []),
            )
        )
        query = self.pagination(query, params.get("page", 1), params.get("size", 25))
        return query

    async def get_latest_activity(self, message, **kwargs):
        entity = message.get("entity")
        for request_id, params in self.request_ids.items():
            device = params.get("query_params").get("device")
            action = params.get("action")

            if device == entity and action == "subscribe":
                _, value = get_non_null_column(message)
                data = {
                    "key_name": message.get("key"),
                    "ts": message.get("ts"),
                    "value": value,
                }
                await self.reply(data=data, action=action, request_id=request_id)

    @action()
    async def subscribe(self, request_id, action, query_params, **kwargs):
        if self.channel_layer is not None:
            await self.channel_layer.group_add("tskv_updates", self.channel_name)
            self.request_ids[request_id] = {"query_params": query_params, "action": action}

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        self.request_ids.pop(request_id, None)

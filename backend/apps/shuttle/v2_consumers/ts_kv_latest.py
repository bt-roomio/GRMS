from djangochannelsrestframework.mixins import ListModelMixin, action

from rest_framework.fields import ValidationError

from shuttle.models import TsKvLatest
from shuttle.serializers.ts_kv_latest import TsKvLatestFilterParams, TsKvLatestSerializer
from shuttle.utils.get_non_null_field import get_non_null_column
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class TsKvLatestConsumer(ListModelMixin, BaseGenericAsyncAPIConsumer):
    queryset = TsKvLatest.objects.all()
    serializer_class = TsKvLatestSerializer

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        params = TsKvLatestFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.get_ts_kv_latest(  # pyright: ignore
            entity=params.get("device"),
            tenant=self.tenant_id,
            sort_by=params.get("sort_by", []),
        )
        return query

    async def ts_kv_latest_activity(self, message, **kwargs):
        updates = message.get("updates", []) or []
        for update in updates:
            await self.handle_ts_kv_latest_activity(update)
        if not updates:
            await self.handle_ts_kv_latest_activity(message.get("update"))

    async def handle_ts_kv_latest_activity(self, message):
        entity = message.get("entity")
        for request_id, params in self.subscribers.items():
            device = params.get("query_params").get("device")
            action = params.get("action")
            response = params.get("response").get("results", [])
            if device == entity and action == "list_subscribe" and await self.has_update(response, message):
                params["response"]["results"] = response
                await self.reply(data=params.get("response"), action=action, request_id=request_id)

            elif device == entity and action == "subscribe":
                _, value = get_non_null_column(message)
                data = {
                    "key_name": message.get("key"),
                    "ts": message.get("ts"),
                    "value": value,
                }
                await self.reply(data=data, action=action, request_id=request_id)

    async def has_update(self, response, message):
        for res in response:
            if res.get("key_name") == message.get("key"):
                res["ts"] = message.get("ts")
                _, res["value"] = get_non_null_column(message)
                return True
        return False

    @action()
    async def subscribe(self, request_id, action, query_params, **kwargs):
        device_id = query_params.get("device")
        if not device_id:
            raise ValidationError("device is required in query_params!")

        await self.add_group(f"tskv_latest_updates_{device_id}")
        self.subscribers[request_id] = {"query_params": query_params, "action": action}

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)

    @action()
    async def list_subscribe(self, request_id, action, query_params, **kwargs):
        data = await self.send_list_paginated(action, query_params, request_id, **kwargs)
        device_id = query_params.get("device")
        await self.add_group(f"tskv_latest_updates_{device_id}")
        self.subscribers[request_id] = {"query_params": query_params, "action": action, "response": data}

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)

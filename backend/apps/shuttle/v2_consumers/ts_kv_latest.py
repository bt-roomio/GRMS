from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import ListModelMixin, action

from rest_framework.fields import ValidationError

from shuttle.models import TsKvLatest
from shuttle.serializers.ts_kv_latest import TsKvLatestFilterParams, TsKvLatestSerializer
from shuttle.utils.get_non_null_field import get_non_null_column
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class TsKvLatestConsumer(ListModelMixin, BaseGenericAsyncAPIConsumer):
    queryset = TsKvLatest.objects.all()
    serializer_class = TsKvLatestSerializer

    async def accept(self, *args, **kwargs):
        self.request_ids = {}
        await super().accept(*args, **kwargs)

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        user = self.scope["user"]
        params = TsKvLatestFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.get_ts_kv_latest(  # pyright: ignore
            entity=params.get("device"), tenant=user.get("tenant_id"), sort_by=params.get("sort_by", [])
        )
        query = self.pagination(query, params.get("page", 1), params.get("size", 25))
        return query

    async def ts_kv_latest_activity(self, message, **kwargs):
        updates = message.get("updates")
        if updates:
            devices = set([u.get("entity") for u in updates])
            for incoming_device in devices:
                for request_id, params in self.request_ids.items():
                    device = params.get("query_params").get("device")
                    action = params.get("action")

                    if device == incoming_device and action == "list_subscribe":
                        data = await sync_to_async(self.get_data)(query_params=params.get("query_params"), **kwargs)
                        await self.reply(data=data, action=action, request_id=request_id)

                    elif device == incoming_device and action == "subscribe":
                        for update in updates:

                            if update.get("entity") == incoming_device:
                                _, value = get_non_null_column(update)
                                data = {
                                    "key_name": update.get("key"),
                                    "ts": update.get("ts"),
                                    "value": value,
                                }
                                await self.reply(data=data, action=action, request_id=request_id)

        if message.get("update"):
            message = message.get("update")
            entity = message.get("entity")
            for request_id, params in self.request_ids.items():
                device = params.get("query_params").get("device")
                action = params.get("action")
                if device == entity and action == "list_subscribe":
                    data = await sync_to_async(self.get_data)(query_params=params.get("query_params"), **kwargs)
                    if any([message.get("key") == i["key_name"] for i in data]):
                        await self.reply(data=data, action=action, request_id=request_id)

                elif device == entity and action == "subscribe":
                    _, value = get_non_null_column(message)
                    data = {
                        "key_name": message.get("key"),
                        "ts": message.get("ts"),
                        "value": value,
                    }
                    await self.reply(data=data, action=action, request_id=request_id)

    @action()
    async def subscribe(self, request_id, action, query_params, **kwargs):
        device_id = query_params.get("device")
        if not device_id:
            raise ValidationError("device is required in query_params!")

        await self.add_group(f"tskv_latest_updates_{device_id}")
        self.request_ids[request_id] = {"query_params": query_params, "action": action}

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        self.request_ids.pop(request_id, None)

    @action()
    async def list_subscribe(self, request_id, action, query_params, **kwargs):
        await self.send_list(action, query_params, request_id, **kwargs)
        device_id = query_params.get("device")
        await self.add_group(f"tskv_latest_updates_{device_id}")
        self.request_ids[request_id] = {"query_params": query_params, "action": action}

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        self.request_ids.pop(request_id, None)

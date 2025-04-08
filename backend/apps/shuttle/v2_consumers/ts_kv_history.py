from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import ListModelMixin, action
from djangochannelsrestframework.observer import model_observer

from shuttle.models import TsKv
from shuttle.serializers.ts_kv import TsKvFilterParams, TsKvSerializer
from shuttle.utils.get_non_null_field import get_non_null_column, get_non_null_field
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class TsKvConsumer(ListModelMixin, BaseGenericAsyncAPIConsumer):
    queryset = TsKv.objects.all()
    serializer_class = TsKvSerializer

    async def accept(self, *args, **kwargs):
        self.request_ids = {}
        await super().accept(*args, **kwargs)

    @action()
    def list(self, **kwargs):  # pyright: ignore
        return self.filter_queryset(self.get_queryset(**kwargs), **kwargs), 200

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        params = TsKvFilterParams.check(data=kwargs.get("query_params", {}))
        result = query.get_history_v2(**params)  # pyright: ignore
        return result

    async def get_latest_activity(self, message, action, **kwargs):
        for request_id, params in self.request_ids.items():
            print(message)
            # device = params.get("device")
            # if device == message.get("entity"):
            #     _, value = get_non_null_column(message)
            #     message = {
            #         "key_name": message.get("key"),
            #         "ts": message.get("ts"),
            #         "value": value,
            #     }
            #     await self.reply(data=message, action=action, request_id=request_id)

    @action()
    async def subscribe(self, request_id, query_params, **kwargs):
        if self.channel_layer is not None:
            await self.channel_layer.group_add("tskv_updates", self.channel_name)
            self.request_ids[request_id] = {"query_params": query_params, "action": action}

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        self.request_ids.pop(request_id, None)

    # @sync_to_async
    # def get_last_updated_obj(self, id, params):
    #     result = {}
    #     query = TsKv.objects.filter(id=id, key__key__in=params.get("keys")).first()
    #     if query:
    #         result["ts"] = query.ts
    #         _, val = get_non_null_field(query)
    #         result["value"] = val
    #     return result
    #
    # async def tskv_update(self, event):
    #     instance_id = event.get("instance_id")
    #
    #     if not self.query_params.get("end_ts"):
    #         result = await self.get_last_updated_obj(id=instance_id, params=self.query_params)
    #         await self.send_json({"message": result, "request_id": self.request_id})
    #
    # @action()
    # async def subscribe(self, request_id, **kwargs):
    #     if self.channel_layer is not None:
    #         await self.channel_layer.group_add("tskv_updates", self.channel_name)
    #         self.request_id = request_id
    #         self.query_params = kwargs.get("query_params", {})

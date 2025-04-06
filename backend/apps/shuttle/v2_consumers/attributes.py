from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import ListModelMixin, action

from shuttle.models import AttributeKv
from shuttle.serializers.attributes import AttributeFilterParams, AttributeSerializer
from shuttle.utils.get_non_null_field import get_non_null_field
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class AttributeConsumer(ListModelMixin, BaseGenericAsyncAPIConsumer):
    queryset = AttributeKv.objects.all()
    serializer_class = AttributeSerializer

    async def accept(self, *args, **kwargs):
        self.request_ids = {}
        await super().accept(*args, **kwargs)

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        params = AttributeFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.get_attributes(  # pyright: ignore
            device=params.get("device"),
            scope=params.get("scope"),
            sort_by=params.get("sort_by", []),
        )
        query = self.pagination(query, params.get("page", 1), params.get("size", 25))
        return query

    @sync_to_async
    def get_last_updated_obj(self, id):
        result = {}
        query = AttributeKv.objects.filter(id=id).first()
        if query:
            result["last_update_ts"] = query.last_update_ts
            result["key_name"] = query.attribute_key
            _, val = get_non_null_field(query)
            result["value"] = val
        return result

    async def attribute_kv_update(self, event):
        instance_id = event.get("instance_id")
        entity_id = event.get("entity_id")

        for request_id, params in self.request_ids.items():
            if params.get("device") == entity_id:
                result = await self.get_last_updated_obj(id=instance_id)
                await self.send_json({"message": result, "request_id": request_id})

    @action()
    async def subscribe(self, request_id, **kwargs):
        if self.channel_layer is not None:
            await self.channel_layer.group_add("attribute_kv_updates", self.channel_name)
            self.request_ids[request_id] = kwargs.get("query_params")

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        self.request_ids.pop(request_id, None)

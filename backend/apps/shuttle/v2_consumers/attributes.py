from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import ListModelMixin

from shuttle.models import AttributeKv
from shuttle.serializers.attributes import AttributeFilterParams, AttributeSerializer
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer
from shuttle.v2_consumers.generics.list_subscribe import ListSubscribeMixin
from shuttle.v2_consumers.generics.subscribe import SubscribeMixin


class AttributeConsumer(ListModelMixin, BaseGenericAsyncAPIConsumer, SubscribeMixin, ListSubscribeMixin):
    queryset = AttributeKv.objects.all()
    serializer_class = AttributeSerializer
    group_name = "attribute_kv_updates"

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

    async def get_latest_activity(self, message):
        updates = message.get("updates", []) or []
        if not updates:
            await self.handle_ts_kv_activity(message.get("update"))
            return

        # Build index of changed (entity, scope) pairs for fast lookup
        changed: dict[tuple, dict] = {}
        for update in updates:
            key = (update.get("entity"), update.get("scope"))
            changed[key] = update

        # Group subscribers by query_params key to avoid redundant DB queries
        list_subs: dict[tuple, list[str]] = {}  # (device, scope) -> [request_id, ...]
        for request_id, params in self.subscribers.items():
            action = params.get("action")
            qp = params.get("query_params", {})
            key = (qp.get("device"), qp.get("scope"))
            if action == "list_subscribe" and key in changed:
                list_subs.setdefault(key, []).append(request_id)
            elif action == "subscribe" and key in changed:
                update = changed[key]
                await self.reply(
                    data={
                        "key_name": update.get("key_name"),
                        "last_update_ts": update.get("last_update_ts"),
                        "value": update.get("value"),
                    },
                    action="subscribe",
                    request_id=request_id,
                )

        # One DB query per unique (device, scope) combination
        for (device, scope), request_ids in list_subs.items():
            data = await sync_to_async(self.get_data)(query_params={"device": device, "scope": scope})
            for request_id in request_ids:
                await self.reply(data=data, action="list_subscribe", request_id=request_id)

    async def handle_ts_kv_activity(self, payload):
        if not payload:
            return
        for request_id, params in self.subscribers.items():
            device = params.get("query_params").get("device")
            scope = params.get("query_params").get("scope")
            action = params.get("action")

            if device == payload.get("entity") and action == "list_subscribe" and scope == payload.get("scope"):
                data = await sync_to_async(self.get_data)(query_params=params.get("query_params"))
                await self.reply(data=data, action="list_subscribe", request_id=request_id)

            elif device == payload.get("entity") and action == "subscribe" and scope == payload.get("scope"):
                payload = {
                    "key_name": payload.get("key_name"),
                    "last_update_ts": payload.get("last_update_ts"),
                    "value": payload.get("value"),
                }
                await self.reply(data=payload, action="subscribe", request_id=request_id)

from asgiref.sync import sync_to_async
from django.db.models import Count, Prefetch
from djangochannelsrestframework.observer.generics import action

from main.models import Device
from main.serializers.device import GatewayListSerializer
from shuttle.models import AttributeKv
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class GatewayConsumer(BaseGenericAsyncAPIConsumer):
    queryset = Device.objects.is_active().filter(additional_info__gateway=True)
    serializer_class = GatewayListSerializer

    async def accept(self, *args, **kwargs):
        self.subscribers = {}
        await super().accept(*args, **kwargs)

    def get_queryset(self, **kwargs):
        qs = (
            super()
            .get_queryset(**kwargs)
            .filter(tenant_id=self.tenant_id)
            .annotate(total_connectors=Count("from_relations"))
        )

        active_attr_qs = AttributeKv.objects.filter(
            attribute_key="active",
            attribute_type=AttributeKv.SERVER_SCOPE,
            entity__in=qs,
        )

        return qs.prefetch_related(Prefetch("attribute_kvs", queryset=active_attr_qs))

    @action()
    def list(self, **kwargs):
        return self.get_data(**kwargs), 200

    async def get_latest_activity(self, message):
        update = message.get("update") or {}
        scope = update.get("scope") in {"CLIENT_SCOPE", "SERVER_SCOPE"}
        key_name = update.get("key_name") == "active"

        for request_id, params in self.subscribers.items():
            query_params = params.get("query_params", {})
            if scope and key_name:
                await self.send_list_paginated(
                    action=params.get("action"), query_params=query_params, request_id=request_id, **params
                )

    @action()
    async def list_subscribe(self, **kwargs):
        await self.send_list_paginated(**kwargs)
        await self.add_group(f"attribute_kv_updates_{self.tenant_id}")
        self.subscribers[kwargs.get("request_id")] = kwargs.get("query_params", {})

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        await self.remove_group(f"attribute_kv_updates_{self.tenant_id}")
        self.subscribers.pop(request_id, None)

from djangochannelsrestframework.observer.generics import action

from fleet.models import FleetNode
from fleet.serializers.fleet_node import FleetNodeSerializer
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class FleetNodeConsumer(BaseGenericAsyncAPIConsumer):
    """
    Live fleet list. The poller pushes into `fleet_nodes_{tenant_id}` on every
    mesh-state change, which is what turns a freshly enrolled node green.
    """

    queryset = FleetNode.objects.is_active()
    serializer_class = FleetNodeSerializer

    async def accept(self, *args, **kwargs):
        self.subscribers = {}
        await super().accept(*args, **kwargs)

    def get_queryset(self, **kwargs):
        return super().get_queryset(**kwargs).filter(tenant_id=self.tenant_id).select_related("tenant")

    @action()
    async def list(self, **kwargs):
        return await self.send_list_paginated(**kwargs), 200

    @action()
    async def list_subscribe(self, **kwargs):
        await self.send_list_paginated(**kwargs)
        await self.add_group(f"fleet_nodes_{self.tenant_id}")
        self.subscribers[kwargs.get("request_id")] = kwargs

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        await self.remove_group(f"fleet_nodes_{self.tenant_id}")
        self.subscribers.pop(request_id, None)

    async def fleet_node_update(self, message):
        for request_id, params in self.subscribers.items():
            await self.send_list_paginated(
                action=params.get("action"),
                query_params=params.get("query_params", {}),
                request_id=request_id,
            )

from djangochannelsrestframework.mixins import action

from main.models import Room
from services.consumers.base import TenantScopedConsumer
from services.serializers.room import RoomFilterSerializer, RoomSerializer


class RoomsConsumer(TenantScopedConsumer):
    serializer_class = RoomSerializer

    async def accept(self, *args, **kwargs):
        self.query_params = {}
        await super().accept(*args, **kwargs)

    def get_queryset(self, **kwargs):
        params = kwargs.get("query_params", {}) or {}
        sort_by = params.get("sort_by", "number")
        if sort_by not in RoomFilterSerializer.SORT_CHOICES:
            sort_by = "number"
        return Room.objects.by_tenant(self.tenant).values("id", "number").order_by(sort_by)

    @action()
    def list(self, query_params=None, **kwargs):
        return self.get_data_paginated(query_params=query_params or {}), 200

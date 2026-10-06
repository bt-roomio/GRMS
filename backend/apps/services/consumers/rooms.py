from djangochannelsrestframework.mixins import action

from rest_framework import serializers

from services.consumers.base import TenantScopedConsumer
from services.querysets.room import room_list
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
        room_type = params.get("room_type")
        if room_type:
            room_type = serializers.UUIDField().run_validation(room_type)
        return room_list(self.tenant, room_type=room_type, sort_by=sort_by)

    @action()
    def list(self, query_params=None, **kwargs):
        return self.get_data_paginated(query_params=query_params or {}), 200

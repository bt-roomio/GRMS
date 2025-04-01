import json

from djangochannelsrestframework.mixins import ListModelMixin, action
from djangochannelsrestframework.observer import model_observer

from main.models import Room
from main.serializers.room import RoomFilterParams, RoomSerializer
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer, UUIDEncoder


class RoomConsumer(ListModelMixin, BaseGenericAsyncAPIConsumer):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        user = self.scope["user"]
        params = RoomFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.list(tenant=user.tenant, sort_by=params.get("sort_by"))  # pyright: ignore
        query = self.pagination(query, params.get("page", 1), params.get("size", 15))
        return query

    @model_observer(Room)
    async def room_latest_activity(self, message, **kwargs):
        subscribing_request_ids = kwargs.get("subscribing_request_ids", [])
        for request_id in subscribing_request_ids:
            await self.send_json({"message": message, "request_id": request_id})

    @room_latest_activity.serializer
    def comment_activity(self, instance: Room, action):
        data = RoomSerializer(instance).data
        return json.dumps(data, cls=UUIDEncoder)

    @action()
    async def subscribe(self, request_id, **kwargs):
        await self.room_latest_activity.subscribe(request_id=request_id, **kwargs)

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        await self.room_latest_activity.unsubscribe(request_id=request_id, **kwargs)

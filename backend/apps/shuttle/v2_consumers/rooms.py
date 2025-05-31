from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import ListModelMixin, action
from djangochannelsrestframework.observer import model_observer

from main.models import Room
from main.serializers.room import RoomFilterParams, RoomSerializer
from shuttle.utils.get_non_null_field import get_non_null_column
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class RoomConsumer(ListModelMixin, BaseGenericAsyncAPIConsumer):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    MUR = "MUR Relay"
    DND = "DND Relay"
    AC_ON_OFF = "AC_ON_OFF"
    Room_Temperature = "Room Temperature"
    Occupancy_State = "Occupancy State"

    STATIC_KEYS = {
        MUR: "MUR Relay",
        DND: "DND Relay",
        AC_ON_OFF: "AC_ON_OFF",
        Room_Temperature: "Room Temperature",
        Occupancy_State: "Occupancy State",
    }

    async def accept(self, *args, **kwargs):
        self.request_ids = {}
        self.scope["user"] = await sync_to_async(self.get_user)()
        await super().accept(*args, **kwargs)

    @action()
    def list(self, **kwargs):  # pyright: ignore
        res = self.get_data_paginated(**kwargs)
        return res, 200

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        user = self.scope["user"]
        params = RoomFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.list(  # pyright: ignore
            tenant=user.get("tenant_id"),
            state=params.get("state"),
            status=params.get("status"),
            search_field=params.get("search_field"),
            search_value=params.get("search_value"),
            sort_by=params.get("sort_by"),
        )
        return query

    async def ts_kv_latest_activity(self, message, **kwargs):
        if message.get("updates"):
            for update in message.get("updates"):
                await self.ts_kv_latest_activity({"update": update}, **kwargs)
            return
        payload = message.get("update")
        if self.STATIC_KEYS.get(payload.get("key")):
            for request_id, _ in self.request_ids.items():
                _, value = get_non_null_column(payload)
                data = {
                    "key_name": payload.get("key"),
                    "ts": payload.get("ts"),
                    "value": value,
                }
                await self.reply(data=data, action="list_subscribe", request_id=request_id)

    @model_observer(Room, serializer_class=RoomSerializer)
    async def get_latest_room_activity(self, message, action, **kwargs):
        for request_id, _ in self.request_ids.items():
            tenant_id = self.scope["user"].get("tenant_id")
            if str(tenant_id) == message.get("tenant"):
                await self.reply(data=message, action=action, request_id=request_id)

    @action()
    async def subscribe(self, request_id, query_params, **kwargs):
        await self.get_latest_room_activity.subscribe(request_id=request_id, **kwargs)
        self.request_ids[request_id] = query_params

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        await self.get_latest_room_activity.unsubscribe(request_id=request_id, **kwargs)

    @model_observer(Room, serializer_class=RoomSerializer)
    async def get_list_activity(self, message, action, **kwargs):
        for request_id, params in self.request_ids.items():
            tenant_id = self.scope["user"].get("tenant_id")
            if str(tenant_id) == message.get("tenant"):
                data = await sync_to_async(self.get_data_paginated)(query_params=params, **kwargs)
                if any([message.get("id") == i["id"] for i in data.get("results", [])]):
                    await self.reply(data=data, action=action, request_id=request_id)

    @action()
    async def list_subscribe(self, request_id, action, query_params, **kwargs):
        data = await self.send_list_paginated(action, query_params, request_id, **kwargs)
        await self.get_list_activity.subscribe(request_id=request_id, **kwargs)
        devices_in_rooms = [j["id"] for i in data.get("results", []) for j in i["devices"]]
        for device_id in devices_in_rooms:
            await self.add_group(f"tskv_latest_updates_{device_id}")
        self.request_ids[request_id] = query_params

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        await self.get_list_activity.unsubscribe(request_id=request_id, **kwargs)

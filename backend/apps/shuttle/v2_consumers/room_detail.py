from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import action

from rest_framework.fields import ValidationError

from main.models import Room
from main.serializers.room import RoomDetailWsSerializer
from shuttle.utils.get_non_null_field import get_non_null_column
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer

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


class RoomDetailConsumer(BaseGenericAsyncAPIConsumer):
    queryset = Room.objects.all()
    serializer_class = RoomDetailWsSerializer
    lookup_field = "pk"

    @staticmethod
    def get_device_id(data):
        return data.get("devices", [])[0].get("id") if isinstance(data, dict) and data.get("devices") else None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keys = list(STATIC_KEYS.keys())
        self.data = None

    async def disconnect(self, code):
        await self.handle_groups(self.data, remove=True)
        await super().disconnect(code)

    @action()
    async def subscribe(self, **kwargs):
        self.keys = [*self.keys, *kwargs.get("keys", [])]
        await self.send_data(**kwargs)
        await self.handle_groups(self.data)

    @action()
    async def unsubscribe(self, **kwargs):
        await self.handle_groups(self.data, remove=True)

    async def send_data(self, **kwargs):
        data = await sync_to_async(self.get)(**kwargs)
        self.data = data
        await self.reply(data=data, action="subscribe", request_id=kwargs.get("request_id"))

    def get(self, **kwargs):
        if kwargs.get("pk") is None:
            raise ValidationError("pk is required in payload!")

        query = self.get_queryset().filter(pk=kwargs.get("pk"))
        instance = query.rooms_ts_kvs(tenant=self.tenant_id, keys=self.keys).first()  # pyright: ignore
        serializer = self.get_serializer(instance=instance, action_kwargs=kwargs)
        return serializer.data

    async def ts_kv_latest_activity(self, message, **kwargs):
        if message.get("updates"):
            for update in message.get("updates"):
                await self.ts_kv_latest_activity({"update": update}, **kwargs)
            return
        payload = message.get("update")
        if payload.get("key") in self.keys:
            incoming_entity_id = payload.get("entity")
            device_id = self.get_device_id(self.data)
            if self.data and device_id and device_id == incoming_entity_id:
                _, value = get_non_null_column(payload)
                self.data["telemetry"][payload.get("key")] = value

        await self.send_json(content=self.data)

    async def handle_groups(self, data, remove=False):
        device_id = self.get_device_id(data)
        if remove:
            await self.remove_group(f"tskv_latest_updates_{device_id}")
        else:
            await self.add_group(f"tskv_latest_updates_{device_id}")

from asgiref.sync import sync_to_async
from django.db.models import Prefetch
from djangochannelsrestframework.mixins import action
from djangochannelsrestframework.observer import model_observer

from rest_framework.fields import ValidationError

from main.models import Guest, Room
from main.serializers.room import RoomDetailWsSerializer
from shuttle.serializers.room_detail import RoomDetailWsFilterBodySerializer
from shuttle.utils.get_non_null_field import get_non_null_column
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class RoomDetailConsumer(BaseGenericAsyncAPIConsumer):
    queryset = Room.objects.all()
    serializer_class = RoomDetailWsSerializer
    lookup_field = "pk"

    def get_device_id(self, request_id):
        data = self.subscribers.get(request_id)
        if not data:
            raise ValidationError("Incorrect request_id!")

        devices = data.get("response", {}).get("devices", []) or []
        if not devices:
            raise ValidationError("There is no device in the room!")

        return devices[0].get("id")

    @model_observer(Room, serializer_class=RoomDetailWsSerializer)  # pyright: ignore
    async def room_activity(self, message, **kwargs):
        for request_id, value in self.subscribers.items():
            pk, keys = value.get("pk"), value.get("keys")
            await self.send_data(request_id=request_id, pk=pk, keys=keys)

    @action()
    async def subscribe(self, request_id, **kwargs):
        body = RoomDetailWsFilterBodySerializer.check(data=kwargs)
        self.subscribers[request_id] = body
        await self.send_data(request_id=request_id, pk=body.get("pk"), keys=body.get("keys"))
        device_id = self.get_device_id(request_id)
        await self.add_group(f"tskv_latest_updates_{device_id}")
        await self.room_activity.subscribe(request_id=request_id, **kwargs)

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        data = self.subscribers.get(request_id)
        if not data:
            return await self.reply(data={"message": "Room not found!"}, action="unsubscribe", request_id=request_id)
        device_id = self.get_device_id(request_id)
        await self.remove_group(f"tskv_latest_updates_{device_id}")
        del self.subscribers[request_id]

    async def send_data(self, request_id, pk, keys):
        data = await sync_to_async(self.get)(pk=pk, keys=keys)
        self.subscribers[request_id]["response"] = data
        await self.reply(data=data, action="subscribe", request_id=request_id)

    def get(self, pk, keys):
        query = self.get_queryset().filter(pk=pk, tenant=self.tenant_id)
        if not query:
            raise ValidationError("Room not found!")

        query = query.prefetch_related(
            Prefetch(
                "guests",
                queryset=Guest.objects.order_by("-created_at")[:1],
                to_attr="last_guests",
            )
        )
        instance = query.rooms_ts_kvs(tenant=self.tenant_id, keys=keys).first()  # pyright: ignore
        serializer = self.get_serializer(instance=instance, action_kwargs={"detail": True})
        return serializer.data

    async def ts_kv_latest_activity(self, message, **kwargs):
        for update in message.get("updates", []) or []:
            await self.ts_kv_latest_activity({"update": update}, **kwargs)
            continue

        for request_id, params in self.subscribers.items():
            payload = message.get("update")
            device_id = self.get_device_id(request_id)

            if (
                payload
                and device_id
                and device_id == payload.get("entity")
                and payload.get("key") in params.get("keys")
            ):
                _, value = get_non_null_column(payload)
                params["response"]["telemetry"][payload.get("key")] = value
                await self.reply(data=params["response"], action="subscribe", request_id=request_id)

from asgiref.sync import sync_to_async
from django.db.models import Prefetch
from djangochannelsrestframework.mixins import action

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
        data = self.request_ids.get(request_id)
        if not data:
            raise ValidationError("Incorrect request_id!")

        devices = data.get("response", {}).get("devices", []) or []
        if not devices:
            raise ValidationError("There is no device in the room!")

        return devices[0].get("id")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_ids = {}

    @action()
    async def subscribe(self, **kwargs):
        body = RoomDetailWsFilterBodySerializer.check(data=kwargs)
        req_id = body.get("request_id")
        self.request_ids[req_id] = body
        await self.send_data(**body)
        device_id = self.get_device_id(req_id)
        await self.add_group(f"tskv_latest_updates_{device_id}")

    @action()
    async def unsubscribe(self, **kwargs):
        req_id = str(kwargs.get("request_id"))
        data = self.request_ids.get(req_id)
        if not data:
            return await self.reply(data={"message": "Room not found!"}, action="unsubscribe", request_id=req_id)
        device_id = self.get_device_id(req_id)
        await self.remove_group(f"tskv_latest_updates_{device_id}")
        del self.request_ids[req_id]

    async def send_data(self, **kwargs):
        req_id = kwargs.get("request_id")
        data = await sync_to_async(self.get)(**kwargs)
        self.request_ids[req_id]["response"] = data
        await self.reply(data=data, action="subscribe", request_id=req_id)

    def get(self, **kwargs):
        query = self.get_queryset().filter(pk=kwargs.get("pk"), tenant=self.tenant_id)
        if not query:
            raise ValidationError("Room not found!")

        query = query.prefetch_related(
            Prefetch(
                "guests",
                queryset=Guest.objects.order_by("-created_at")[:1],
                to_attr="last_guests",
            )
        )
        instance = query.rooms_ts_kvs(tenant=self.tenant_id, keys=kwargs.get("keys")).first()  # pyright: ignore
        serializer = self.get_serializer(instance=instance, action_kwargs=kwargs)
        return serializer.data

    async def ts_kv_latest_activity(self, message, **kwargs):
        for update in message.get("updates", []) or []:
            await self.ts_kv_latest_activity({"update": update}, **kwargs)
            return

        for request_id, params in self.request_ids.items():
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

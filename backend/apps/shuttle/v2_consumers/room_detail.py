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

    def get_device_ids(self, request_id) -> list[str]:
        data = self.subscribers.get(request_id)
        if not data:
            raise ValidationError("Incorrect request_id!")

        devices = data.get("response", {}).get("devices", []) or []
        return [device_id for device in devices if (device_id := device.get("id"))]

    async def get_activity(self, message, **kwargs):
        for request_id, value in self.subscribers.items():
            pk, keys = value.get("pk"), value.get("keys")
            await self.send_data(request_id=request_id, pk=pk, keys=keys)

    @action()
    async def subscribe(self, request_id, **kwargs):
        body = RoomDetailWsFilterBodySerializer.check(data=kwargs)
        self.subscribers[request_id] = {**body, "action": kwargs.get("action")}
        await self.send_data(request_id=request_id, pk=body.get("pk"), keys=body.get("keys"))
        for device_id in self.get_device_ids(request_id):
            await self.add_group(f"tskv_latest_updates_{device_id}")
        await self.add_group(f"room_detail_{body.get('pk')}")

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        data = self.subscribers.get(request_id)
        if not data:
            return await self.reply(data={"message": "Room not found!"}, action="unsubscribe", request_id=request_id)
        for device_id in self.get_device_ids(request_id):
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
                queryset=Guest.objects.filter(tenant_id=self.tenant_id, is_active=True, is_reservation=False).order_by(
                    "-created_at"
                )[:1],
                to_attr="last_guests",
            )
        )
        instance = query.rooms_ts_kvs(tenant=self.tenant_id, keys=keys).first()  # ty: ignore
        serializer = self.get_serializer(instance=instance, action_kwargs={"detail": True})
        return serializer.data

    async def ts_kv_latest_activity(self, message, **kwargs):
        # Поддерживаем оба формата: батч ("updates": [...]) и одиночный ("update": {...}).
        single = message.get("update")
        updates = message.get("updates") or ([single] if single else [])
        if not updates:
            return

        for request_id, params in self.subscribers.items():
            device_ids = self.get_device_ids(request_id)
            keys = params.get("keys") or ()

            for payload in updates:
                if not payload:
                    continue
                if payload.get("entity") in device_ids and payload.get("key") in keys:
                    _, value = get_non_null_column(payload)
                    params["response"]["telemetry"][payload.get("key")] = value
                    await self.reply(data=params["response"], action="subscribe", request_id=request_id)

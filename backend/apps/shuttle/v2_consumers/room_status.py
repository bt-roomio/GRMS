from asgiref.sync import sync_to_async
from djangochannelsrestframework.observer.generics import action

from main.models import Device, Room
from main.serializers.room_status import RoomLiveStatusSerializer
from shuttle.models import TsKvLatest
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class RoomStatusConsumer(BaseGenericAsyncAPIConsumer):
    queryset = TsKvLatest.objects.all()
    serializer_class = RoomLiveStatusSerializer

    async def response(self):
        tenant_id = self.tenant_id
        flag_counts = await sync_to_async(self.queryset.room_flag_counts)(tenant_id)  # pyright: ignore
        offline = await sync_to_async(Device.objects.offline_count)(tenant_id)
        checked_in = await sync_to_async(Room.objects.checked_in_count)(tenant_id)
        available = await sync_to_async(Room.objects.available_count)(tenant_id)

        base = {
            "available": available,
            "checkedin": checked_in,
            "offline": offline,
            **flag_counts,
        }
        serializer = self.serializer_class(instance=base)
        return serializer.data

    async def get_latest_activity(self, message):
        for request_id, params in self.subscribers.items():
            data = await self.response()
            if data == params.get("response"):
                return
            await self.reply(data=data, action=params.get("action"), request_id=request_id)

    @action()
    async def list_subscribe(self, request_id, action, query_params):
        await self.add_group(f"room_status_{self.tenant_id}")
        res = await self.response()
        self.subscribers[request_id] = {"query_params": query_params, "action": action, "response": res}
        await self.reply(data=res, action=action, request_id=request_id)

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        await self.remove_group(f"room_status_{self.tenant_id}")
        self.subscribers.pop(request_id, None)

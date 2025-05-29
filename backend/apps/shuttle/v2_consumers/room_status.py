from asgiref.sync import sync_to_async
from djangochannelsrestframework.observer.generics import action

from shuttle.consumers.aggregations.controller_status import controller_status
from shuttle.models import TsKvDictionary, TsKvLatest
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class RoomStatusConsumer(BaseGenericAsyncAPIConsumer):
    async def accept(self, *args, **kwargs):
        self.subscribers = {}
        self.user = self.scope["user"]
        self.user_obj = await sync_to_async(self.get_user_object)()
        await super().accept(*args, **kwargs)

    @action()
    async def list_subscribe(self, request_id, action, **kwargs):
        await self.add_group("room_status")
        self.subscribers[request_id] = {"action": action}
        await self.get_latest_activity(request_id=request_id)

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)

    async def get_latest_activity(self, message=None, request_id=None, **kwargs):
        if message and message.get("updates"):
            for update in message.get("updates"):
                await self.get_latest_activity(update, **kwargs)

        user_obj = self.user_obj
        tenant_id = getattr(self.user, "tenant_id", None)
        request_ids = [request_id] if request_id is not None else self.subscribers.keys()
        for request_id in request_ids:
            dnd_count = await self.get_room_count_by_key("DND Relay", tenant_id)
            mur_count = await self.get_room_count_by_key("MUR Relay", tenant_id)
            occupancy_count = await self.get_room_count_by_key("Occupancy State", tenant_id)
            raw_stats = await controller_status({}, user_obj)
            flat_data = await self.flatten_controller_status(raw_stats)
            flat_data.update(
                {
                    "dnd": dnd_count,
                    "mur": mur_count,
                    "occupied": occupancy_count,
                }
            )
            await self.reply(data=flat_data, action="list_subscribe", request_id=request_id)

    async def flatten_controller_status(self, data: dict) -> dict:
        result = {}
        status_controllers = data.get("data", {}).get("status_controllers", [])
        for item in status_controllers:
            status = item.get("status").lower()
            count = item.get("last_24_hour", 0)
            if status:
                result[status] = count
        count_active_rooms = data.get("data", {}).get("count_active_rooms", [])
        for item in count_active_rooms:
            if item.get("status") is False:
                result["offline"] = item.get("count", 0)
                break
        return result

    @sync_to_async
    def get_room_count_by_key(self, key_name: str, tenant_id):
        key_id = TsKvDictionary.objects.filter(key=key_name).values_list("key_id", flat=True).first()
        if key_id is None:
            return 0
        return TsKvLatest.objects.filter(key=key_id, long_v=1, entity__tenant_id=tenant_id).count()

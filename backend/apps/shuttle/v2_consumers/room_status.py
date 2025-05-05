from asgiref.sync import sync_to_async
from djangochannelsrestframework.observer.generics import action
from shuttle.consumers.aggregations.controller_status import controller_status
from shuttle.models import TsKvDictionary, TsKvLatest, AttributeKv
from shuttle.serializers.attributes import AttributeSerializer
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class RoomStatusConsumer(BaseGenericAsyncAPIConsumer):

    async def accept(self, *args, **kwargs):
        self.subscribers = {}
        self.user = self.scope["user"]
        self.user_obj = await sync_to_async(self.get_user_object)()
        await super().accept(*args, **kwargs)

    async def get_latest_activity(self, message, **kwargs):
        user_obj = self.user_obj
        tenant_id = getattr(self.user, "tenant_id", None)
        for request_id, params in self.subscribers.items():
            dnd_count = await self.get_room_count_by_key("DND Relay", tenant_id)
            mur_count = await self.get_room_count_by_key("MUR Relay", tenant_id)
            occupancy_count = await self.get_room_count_by_key("Occupancy State", tenant_id)
            raw_stats = await controller_status({}, user_obj)
            flat_data = await self.flatten_controller_status(raw_stats)

            flat_data.update(
                {
                    "dnd": {"status": True, "count": dnd_count},
                    "mur": {"status": True, "count": mur_count},
                    "occupied": {"status": True, "count": occupancy_count},
                }
            )

            await self.reply(data=flat_data, action="subscribe", request_id=request_id)

    async def flatten_controller_status(self, raw_status):
        flat = {}
        data = raw_status.get("data", {})

        for entry in data.get("status_controllers", []):
            name = entry.get("status")
            if name:
                flat[name] = {
                    "last_24_hour": entry.get("last_24_hour", 0),
                    "diff_previous_day": entry.get("diff_previous_day", 0),
                }

        # # Flatten count_active_rooms
        # for idx, entry in enumerate(data.get("count_active_rooms", [])):
        #     flat[f"count_active_room_{idx}"] = entry  # optionally rename to something better

        raw_status.pop("subscriptionId", None)
        return flat

    @sync_to_async
    def get_room_count_by_key(self, key_name: str, tenant_id):
        key_id = TsKvDictionary.objects.filter(key=key_name).values_list("key_id", flat=True).first()
        if key_id is None:
            return 0
        return TsKvLatest.objects.filter(key=key_id, long_v=1, entity__tenant_id=tenant_id).count()

    @action()
    async def subscribe(self, request_id, action, **kwargs):
        if self.channel_layer is not None:
            await self.channel_layer.group_add("room_status", self.channel_name)
            self.subscribers[request_id] = {"action": action}

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)

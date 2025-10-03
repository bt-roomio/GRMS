from asgiref.sync import sync_to_async
from djangochannelsrestframework.observer.generics import action

from shuttle.consumers.aggregations.controller_status import controller_status
from shuttle.models import TsKvDictionary, TsKvLatest
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer

DND_RELAY = "DND Relay"
MUR_RELAY = "MUR Relay"
OCCUPANCY_STATE = "Occupancy State"
AC_ON_OFF = "AC ON OFF"


class RoomStatusConsumer(BaseGenericAsyncAPIConsumer):
    async def response(self):
        dnd_count = await self.get_room_count_by_key(DND_RELAY, self.tenant_id)
        mur_count = await self.get_room_count_by_key(MUR_RELAY, self.tenant_id)
        occupancy_count = await self.get_room_count_by_key(OCCUPANCY_STATE, self.tenant_id)
        ac_on_off = await self.get_room_count_by_key(AC_ON_OFF, self.tenant_id)
        raw_stats = await controller_status({}, self.tenant_id)
        flat_data = await self.flatten_controller_status(raw_stats)
        flat_data.update(
            {
                "dnd": dnd_count,
                "mur": mur_count,
                "occupied": occupancy_count,
                "ac-on-off": ac_on_off,
            }
        )

        return flat_data

    @action()
    async def list_subscribe(self, request_id, action, query_params):
        await self.add_group("room_status")
        res = await self.response()
        self.subscribers[request_id] = {"query_params": query_params, "action": action, "response": res}
        await self.reply(data=res, action=action, request_id=request_id)

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        await self.remove_group("room_status")
        self.subscribers.pop(request_id)

    async def get_latest_activity(self, message):
        if message and message.get("updates"):
            for update in message.get("updates"):
                await self.get_latest_activity(update)

        key = message.get("key")
        for request_id, params in self.subscribers.items():
            if key in [DND_RELAY, MUR_RELAY, OCCUPANCY_STATE]:
                data = await self.response()
                await self.reply(data=data, action=params.get("action"), request_id=request_id)

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
        return TsKvLatest.objects.filter(
            key=key_id, long_v=1, entity__room__isnull=False, entity__tenant_id=tenant_id
        ).count()

from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import ListModelMixin, action
from djangochannelsrestframework.observer import model_observer

from main.models import Room
from main.querysets.room import RoomQuerySet
from main.serializers.room import RoomFilterParams, RoomSerializer
from shuttle.constants import STATIC_KEYS
from shuttle.utils.get_non_null_field import get_non_null_column
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class RoomConsumer(ListModelMixin, BaseGenericAsyncAPIConsumer):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    async def accept(self, *args, **kwargs):
        self.query_params = {}
        self.responses = {}
        self.device_groups: set[str] = set()
        self.changed_room_ids: set[str] = set()
        self.changed_room_action = None
        await super().accept(*args, **kwargs)

    @action()
    def list(self, **kwargs):  # pyright: ignore
        res = self.get_data_paginated(**kwargs)
        return res, 200

    def get_queryset(self, **kwargs):
        query: RoomQuerySet = super().get_queryset(**kwargs)  # ty: ignore
        params = RoomFilterParams.check(data=kwargs.get("query_params", {}))
        query = (
            query.list(
                tenant=self.tenant_id,
                state=params.get("state"),
                status=params.get("status"),
                search_field=params.get("search_field"),
                search_value=params.get("search_value"),
                sort_by=params.get("sort_by"),
                blocks=params.get("blocks"),
            )
            .guest_details()
            .rooms_ts_kvs(tenant=self.tenant_id, keys=[*STATIC_KEYS])
            .get_tags(tenant=self.tenant_id, tags=params.get("tags", []))
        )
        return query

    async def ts_kv_latest_activity(self, message, **kwargs):
        if message.get("updates"):
            for update in message.get("updates"):
                await self.ts_kv_latest_activity({"update": update}, **kwargs)
            return

        payload = message.get("update")
        if payload.get("key") in STATIC_KEYS:
            for request_id, _ in self.query_params.items():
                incoming_entity_id = payload.get("entity")
                updated = False
                for room in self.responses.get(request_id, {}).get("results", []):
                    has_device = room.get("devices", [])
                    if has_device and has_device[0].get("id") == incoming_entity_id:
                        _, value = get_non_null_column(payload)
                        room["telemetry"][payload.get("key")] = value
                        updated = True
                        break

                if updated:
                    await self.reply(data=self.responses[request_id], action="list_subscribe", request_id=request_id)
            return

        for request_id, params in self.subscribers.items():
            tags = params.get("query_params").get("tags", [])
            action = params.get("action")
            response = self.responses.get(request_id, {})
            updated = False
            for tag in tags:
                if tag.get("name") == payload.get("key") and tag.get("tag_type") == "telemetry":
                    results = response.get("results", [])
                    for room in results:
                        has_device = room.get("devices", [])
                        if has_device and has_device[0].get("id") == payload.get("entity"):
                            for field in room.get("additional_fields", []):
                                if payload.get("key") in field:
                                    field[payload.get("key")] = payload.get("value")
                            updated = True
                            break

                    response["results"] = results

            if updated:
                await self.reply(data=response, action=action, request_id=request_id)

    async def get_latest_activity(self, message, **kwargs):
        if message.get("updates"):
            for update in message.get("updates"):
                await self.get_latest_activity({"update": update}, **kwargs)
            return

        payload = message.get("update") or {}
        if not payload:
            return

        for request_id, params in self.subscribers.items():
            tags = params.get("query_params").get("tags", [])
            action = params.get("action")
            response = self.responses.get(request_id, {})
            updated = False
            for tag in tags:
                if tag.get("name") == payload.get("key_name") and tag.get("attribute_scope") == payload.get("scope"):
                    results = response.get("results", [])
                    for room in results:
                        has_device = room.get("devices", [])
                        if has_device and has_device[0].get("id") == payload.get("entity"):
                            for field in room.get("additional_fields", []):
                                if payload.get("key_name") in field and field.get("attribute_scope") == payload.get(
                                    "scope"
                                ):
                                    field[payload.get("key_name")] = payload.get("value")
                            updated = True
                            break

                    response["results"] = results

            if updated:
                await self.reply(data=response, action=action, request_id=request_id)

    # Both observers are partitioned by tenant: by default DCRF sends every
    # save of any room to one shared group, and consumers of every hotel
    # received (and discarded) other tenants' events.
    @model_observer(Room, serializer_class=RoomSerializer)
    async def get_latest_room_activity(self, message, action, **kwargs):
        for request_id, _ in self.query_params.items():
            if str(self.tenant_id) == message.get("tenant"):
                await self.reply(data=message, action=action, request_id=request_id)

    @get_latest_room_activity.groups_for_signal
    def get_latest_room_activity(self, instance=None, **kwargs):
        yield f"tenant-{instance.tenant_id}"

    @get_latest_room_activity.groups_for_consumer
    def get_latest_room_activity(self, tenant_id=None, **kwargs):
        yield f"tenant-{tenant_id}"

    @action()
    async def subscribe(self, request_id, query_params, **kwargs):
        await self.get_latest_room_activity.subscribe(request_id=request_id, tenant_id=self.tenant_id)
        self.query_params[request_id] = query_params

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        await self.get_latest_room_activity.unsubscribe(request_id=request_id, tenant_id=self.tenant_id)

    @model_observer(Room, serializer_class=RoomSerializer)
    async def get_list_activity(self, message, action, **kwargs):
        if str(self.tenant_id) != message.get("tenant"):
            return
        # Bulk room changes (check-ins, PMS sync) used to trigger a full
        # page re-query per room; now it is one per burst.
        self.changed_room_ids.add(str(message.get("id")))
        self.changed_room_action = action
        self.request_refresh(self.refresh_room_lists)

    async def refresh_room_lists(self):
        changed, self.changed_room_ids = self.changed_room_ids, set()
        action = self.changed_room_action
        for request_id, params in list(self.query_params.items()):
            previous = self.responses.get(request_id) or {}
            data = await sync_to_async(self.get_data_paginated)(query_params=params)
            if request_id in self.responses:
                self.responses[request_id] = data
            # Look at the previous response too: a deleted room, or one that dropped out of the filter,
            # exists only there, and the client must get the page without it.
            shown = {str(i["id"]) for i in data.get("results", [])}
            shown.update(str(i["id"]) for i in previous.get("results", []))
            if shown & changed:
                await self.reply(data=data, action=action, request_id=request_id)
        await self.sync_device_groups()

    @get_list_activity.groups_for_signal
    def get_list_activity(self, instance=None, **kwargs):
        yield f"tenant-{instance.tenant_id}"

    @get_list_activity.groups_for_consumer
    def get_list_activity(self, tenant_id=None, **kwargs):
        yield f"tenant-{tenant_id}"

    @action()
    async def list_subscribe(self, request_id, action, query_params, **kwargs):
        data = await self.send_list_paginated(action, query_params, request_id, **kwargs)

        await self.get_list_activity.subscribe(request_id=request_id, tenant_id=self.tenant_id)
        self.responses[request_id] = data
        self.query_params[request_id] = query_params
        self.subscribers[request_id] = {"query_params": query_params, "action": action}
        await self.sync_device_groups()

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        await self.get_list_activity.unsubscribe(request_id=request_id, tenant_id=self.tenant_id)
        self.responses.pop(request_id, None)
        self.subscribers.pop(request_id, None)
        self.query_params.pop(request_id, None)
        await self.sync_device_groups()

    async def sync_device_groups(self):
        """Align telemetry subscriptions with the devices from all current responses.

        Groups are computed over the union of all request_ids, so unsubscribing or changing
        the page of one request doesn't remove groups another one needs.
        """
        wanted = {
            f"tskv_latest_updates_{device['id']}"
            for data in self.responses.values()
            for room in (data or {}).get("results", [])
            for device in room.get("devices", [])
        }
        if wanted:
            wanted.add(f"attribute_kv_updates_{self.tenant_id}")

        for group in self.device_groups - wanted:
            await self.remove_group(group)
        for group in wanted - self.device_groups:
            await self.add_group(group)
        self.device_groups = wanted

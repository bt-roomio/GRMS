from asgiref.sync import sync_to_async
from django.db.models import F
from djangochannelsrestframework.mixins import action

from rest_framework.exceptions import ValidationError

from core.serializers.pagination import PaginationSerializer
from main.models import Room
from services.consumers.base import TenantScopedConsumer
from services.serializers.room import RoomSerializer
from services.serializers.tag import TagSerializer
from services.utils.room_tags import paginated_room_tags, resolve_tag


def _updates_in_message(message) -> list:
    updates = message.get("updates")
    if updates is None:
        update = message.get("update")
        updates = [update] if update else []
    return [u for u in updates if u]


class RoomTagsConsumer(TenantScopedConsumer):
    serializer_class = TagSerializer

    async def accept(self, *args, **kwargs):
        self.subscribers = {}
        await super().accept(*args, **kwargs)

    def get_room(self, room_id):
        room = Room.objects.by_tenant(self.tenant).annotate(type_name=F("type__title")).filter(pk=room_id).first()
        if room is None:
            raise ValidationError("Room not found!")
        return room

    def build_payload(self, query_params, mapper=None):
        room = self.get_room(query_params.get("room_id"))
        params = PaginationSerializer.parse(query_params)
        device_ids = [str(device_id) for device_id in room.devices.values_list("id", flat=True)]
        tags = paginated_room_tags(room, self.tenant, params.page, params.size, mapper or self.get_mapper())
        return {"room": RoomSerializer(room).data, **tags}, device_ids

    @action()
    async def list(self, request_id, query_params=None, **kwargs):  # pyright: ignore
        payload, _ = await sync_to_async(self.build_payload)(query_params or {})
        await self.reply(data=payload, action="list", request_id=request_id)

    @action()
    async def subscribe(self, request_id, query_params=None, **kwargs):
        query_params = query_params or {}
        payload, device_ids = await sync_to_async(self.build_payload)(query_params)
        self.subscribers[request_id] = {"query_params": query_params, "device_ids": device_ids}

        await self.add_group(f"attribute_kv_updates_{self.tenant_id}")
        for device_id in device_ids:
            await self.add_group(f"tskv_latest_updates_{device_id}")
        await self.reply(data=payload, action="subscribe", request_id=request_id)

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        data = self.subscribers.pop(request_id, None)
        if not data:
            return
        for device_id in data["device_ids"]:
            if not any(device_id in s["device_ids"] for s in self.subscribers.values()):
                await self.remove_group(f"tskv_latest_updates_{device_id}")
        if not self.subscribers:
            await self.remove_group(f"attribute_kv_updates_{self.tenant_id}")

    async def _resend(self, message):
        entities = {str(u.get("entity")) for u in _updates_in_message(message) if u.get("entity")}
        mapper = None  # one per update, shared by the subscriptions it reaches
        for request_id, sub in self.subscribers.items():
            if entities and entities.isdisjoint(sub["device_ids"]):
                continue
            mapper = mapper or await sync_to_async(self.get_mapper)()
            payload, device_ids = await sync_to_async(self.build_payload)(sub["query_params"], mapper)
            for device_id in set(device_ids) - set(sub["device_ids"]):
                await self.add_group(f"tskv_latest_updates_{device_id}")
            sub["device_ids"] = device_ids
            await self.reply(data=payload, action="subscribe", request_id=request_id)

    async def get_latest_activity(self, message, **kwargs):
        await self._resend(message)

    async def ts_kv_latest_activity(self, message, **kwargs):
        await self._resend(message)


class TagDetailConsumer(TenantScopedConsumer):
    """One tag by id: a plain one, one a composite rule computes, or a virtual one. A composite
    tag is resent when any of its inputs changes on a device of its room."""

    serializer_class = TagSerializer

    async def accept(self, *args, **kwargs):
        self.subscribers = {}
        await super().accept(*args, **kwargs)

    def build_payload(self, tag_id, mapper=None):
        """The tag and what to watch for it."""
        resolved = resolve_tag(self.tenant, tag_id, mapper or self.get_mapper())
        entity_ids, tag_names = resolved.watch
        return resolved.data, {
            "entity_ids": entity_ids,
            "tag_names": tag_names,
            "composite": resolved.binding is not None,
        }

    @action()
    async def retrieve(self, request_id, query_params=None, **kwargs):  # pyright: ignore
        payload, _ = await sync_to_async(self.build_payload)((query_params or {}).get("tag_id"))
        await self.reply(data=payload, action="retrieve", request_id=request_id)

    @action()
    async def subscribe(self, request_id, query_params=None, **kwargs):
        tag_id = (query_params or {}).get("tag_id")
        payload, watch = await sync_to_async(self.build_payload)(tag_id)
        self.subscribers[request_id] = {"tag_id": tag_id, **watch}

        await self.add_group(f"attribute_kv_updates_{self.tenant_id}")
        for entity_id in watch["entity_ids"]:
            await self.add_group(f"tskv_latest_updates_{entity_id}")
        await self.reply(data=payload, action="subscribe", request_id=request_id)

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        data = self.subscribers.pop(request_id, None)
        if not data:
            return
        for entity_id in data["entity_ids"]:
            if not any(entity_id in s["entity_ids"] for s in self.subscribers.values()):
                await self.remove_group(f"tskv_latest_updates_{entity_id}")
        if not self.subscribers:
            await self.remove_group(f"attribute_kv_updates_{self.tenant_id}")

    async def _resend(self, message):
        updates = _updates_in_message(message)
        mapper = None  # one per update, shared by the subscriptions it reaches
        for request_id, sub in self.subscribers.items():
            # A value the tag shows (its own, or an input of a composite tag) or its device's
            # TAG_TYPES (tag_type / tag_ranges) changed. A composite tag matches an input name on any
            # device: one that joined its room since is not watched yet, the rebuild tells.
            matched = any(
                (sub["composite"] or str(u.get("entity")) in sub["entity_ids"])
                and sub["tag_names"] & {u.get("key"), u.get("key_name")}
                for u in updates
            )
            if not matched:
                continue
            mapper = mapper or await sync_to_async(self.get_mapper)()
            payload, watch = await sync_to_async(self.build_payload)(sub["tag_id"], mapper)
            # A device joined the room or the rule's inputs changed: watch what the tag reads now.
            for entity_id in watch["entity_ids"] - sub["entity_ids"]:
                await self.add_group(f"tskv_latest_updates_{entity_id}")
            sub.update(watch)
            await self.reply(data=payload, action="subscribe", request_id=request_id)

    async def get_latest_activity(self, message, **kwargs):
        await self._resend(message)

    async def ts_kv_latest_activity(self, message, **kwargs):
        await self._resend(message)

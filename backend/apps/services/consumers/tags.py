from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import action

from rest_framework.exceptions import NotFound, ValidationError

from main.models import Room
from services.consumers.base import TenantScopedConsumer
from services.serializers.room import RoomSerializer
from services.serializers.tag import RoomAttributeTagSerializer, RoomTelemetryTagSerializer, TagSerializer
from shuttle.models import AttributeKv, TsKvLatest


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
        room = Room.objects.by_tenant(self.tenant).filter(pk=room_id).first()
        if room is None:
            raise ValidationError("Room not found!")
        return room

    def build_payload(self, room_id):
        room = self.get_room(room_id)
        attributes = AttributeKv.objects.get_attributes_by_room(room, AttributeKv.CLIENT_SCOPE)
        telemetry = TsKvLatest.objects.get_ts_kv_latest_by_room(room, self.tenant)
        device_ids = [str(device_id) for device_id in room.devices.values_list("id", flat=True)]
        tags = [
            *RoomAttributeTagSerializer(attributes, many=True).data,
            *RoomTelemetryTagSerializer(telemetry, many=True).data,
        ]
        payload = {
            "room": RoomSerializer(room).data,
            "tags": tags,
        }
        return payload, device_ids

    @action()
    async def list(self, request_id, query_params=None, **kwargs):  # pyright: ignore
        payload, _ = await sync_to_async(self.build_payload)((query_params or {}).get("room_id"))
        await self.reply(data=payload, action="list", request_id=request_id)

    @action()
    async def subscribe(self, request_id, query_params=None, **kwargs):
        room_id = (query_params or {}).get("room_id")
        payload, device_ids = await sync_to_async(self.build_payload)(room_id)
        self.subscribers[request_id] = {"room_id": room_id, "device_ids": device_ids}

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
        for request_id, sub in self.subscribers.items():
            if entities and entities.isdisjoint(sub["device_ids"]):
                continue
            payload, _ = await sync_to_async(self.build_payload)(sub["room_id"])
            await self.reply(data=payload, action="subscribe", request_id=request_id)

    async def get_latest_activity(self, message, **kwargs):
        await self._resend(message)

    async def ts_kv_latest_activity(self, message, **kwargs):
        await self._resend(message)


class TagDetailConsumer(TenantScopedConsumer):
    serializer_class = TagSerializer

    async def accept(self, *args, **kwargs):
        self.subscribers = {}
        await super().accept(*args, **kwargs)

    def get_tag(self, tag_id):
        tag = AttributeKv.objects.select_related("entity").filter(entity__tenant=self.tenant, pk=tag_id).first()
        if tag is None:
            tag = (
                TsKvLatest.objects.select_related("entity", "key").filter(entity__tenant=self.tenant, pk=tag_id).first()
            )
        if tag is None:
            raise NotFound("Tag not found.")
        return tag

    def build_payload(self, tag_id):
        tag = self.get_tag(tag_id)
        key_name = tag.attribute_key if isinstance(tag, AttributeKv) else tag.key.key
        return TagSerializer(tag).data, str(tag.entity_id), key_name

    @action()
    async def retrieve(self, request_id, query_params=None, **kwargs):  # pyright: ignore
        payload, _, _ = await sync_to_async(self.build_payload)((query_params or {}).get("tag_id"))
        await self.reply(data=payload, action="retrieve", request_id=request_id)

    @action()
    async def subscribe(self, request_id, query_params=None, **kwargs):
        tag_id = (query_params or {}).get("tag_id")
        payload, entity_id, key_name = await sync_to_async(self.build_payload)(tag_id)
        self.subscribers[request_id] = {"tag_id": tag_id, "entity_id": entity_id, "key_name": key_name}

        await self.add_group(f"attribute_kv_updates_{self.tenant_id}")
        await self.add_group(f"tskv_latest_updates_{entity_id}")
        await self.reply(data=payload, action="subscribe", request_id=request_id)

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        data = self.subscribers.pop(request_id, None)
        if not data:
            return
        entity_id = data["entity_id"]
        if not any(entity_id == s["entity_id"] for s in self.subscribers.values()):
            await self.remove_group(f"tskv_latest_updates_{entity_id}")
        if not self.subscribers:
            await self.remove_group(f"attribute_kv_updates_{self.tenant_id}")

    async def _resend(self, message):
        updates = _updates_in_message(message)
        for request_id, sub in self.subscribers.items():
            matched = any(
                str(u.get("entity")) == sub["entity_id"] and sub["key_name"] in (u.get("key"), u.get("key_name"))
                for u in updates
            )
            if not matched:
                continue
            payload, _, _ = await sync_to_async(self.build_payload)(sub["tag_id"])
            await self.reply(data=payload, action="subscribe", request_id=request_id)

    async def get_latest_activity(self, message, **kwargs):
        await self._resend(message)

    async def ts_kv_latest_activity(self, message, **kwargs):
        await self._resend(message)

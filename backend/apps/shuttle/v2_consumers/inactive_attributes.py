from asgiref.sync import sync_to_async
from django.db.models import Q
from djangochannelsrestframework.mixins import action

from shuttle.models import AttributeKv
from shuttle.serializers.attributes import InactiveAttributesFilterParams, InactiveDeviceAttributeSerializer
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class InactiveDeviceAttributeConsumer(BaseGenericAsyncAPIConsumer):
    queryset = AttributeKv.objects.all()
    serializer_class = InactiveDeviceAttributeSerializer

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("context", {})
        kwargs["context"].update({"exclude_room_obj": False})
        return super().get_serializer(*args, **kwargs)

    def get_data_paginated(self, query_params, **kwargs):
        data = self.get_queryset(query_params=query_params)
        data = self.get_serializer(instance=data, many=True, action_kwargs=kwargs).data
        return data

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        params = InactiveAttributesFilterParams.check(data=kwargs.get("query_params", {}) or {})
        tenant_id = self.tenant_id

        query = query.inactive_devices_in_spaces(  # type: ignore[attr-defined]
            tenant_id=tenant_id,
            sort_by=params.get("sort_by", "-last_update_ts"),
        )
        page = params.get("page", 1)
        size = params.get("size", 25)
        return self.pagination(query, page, size)

    async def get_latest_activity(self, message):
        updates = message.get("updates", []) or []
        if updates:
            for u in updates:
                await self._maybe_push(u)
        else:
            await self._maybe_push(message.get("update"))

    async def _maybe_push(self, payload):
        if not payload or payload.get("scope") != "SERVER_SCOPE" or payload.get("key_name") != "active":
            return

        device_id = payload.get("entity")
        if not device_id:
            return

        from main.models import Device

        tenant_id = self.tenant_id
        device_connected = await sync_to_async(
            lambda: Device.objects.filter(id=device_id, tenant_id=tenant_id)
            .filter(Q(room__isnull=False) | Q(device_public_spaces__isnull=False))
            .exists()
        )()
        if not device_connected:
            return

        for request_id, params in self.subscribers.items():
            if params.get("action") == "list_subscribe":
                data = await sync_to_async(self.get_data)(query_params=params.get("query_params"))
                await self.reply(data=data, action="list_subscribe", request_id=request_id)

    @action()
    async def list_subscribe(self, request_id, query_params, action):
        res = await self.send_list_paginated(action, query_params, request_id)
        await self.add_group(f"attribute_kv_updates_{self.tenant_id}")
        self.subscribers[request_id] = {"query_params": query_params, "action": action, "response": res}

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)

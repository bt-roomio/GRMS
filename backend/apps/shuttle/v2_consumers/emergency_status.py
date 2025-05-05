from asgiref.sync import sync_to_async
from djangochannelsrestframework.observer.generics import action
from main.models import Device
from shuttle.models import TsKvDictionary, TsKvLatest
from shuttle.serializers.emergency_status import EmergencyStatusFilterParams
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer
from djangochannelsrestframework.mixins import ListModelMixin


class EmergencyStatus(ListModelMixin, BaseGenericAsyncAPIConsumer):
    queryset = Device.objects.all()

    async def accept(self, *args, **kwargs):
        self.subscribers = {}
        self.user = self.scope["user"]
        await super().accept(*args, **kwargs)

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        user = self.user
        params = EmergencyStatusFilterParams.check(data=kwargs.get("query_params", {}))

        if params.get("room_types"):
            query = query.filter(room__type__title__in=params["room_types"])

        if params.get("delisting_devices"):
            query = query.exclude(id__in=params["delisting_devices"])

        query = query.filter(tenant=user.tenant_id).select_related("room")
        return query

    @action()
    async def subscribe(self, request_id, action, **kwargs):
        if self.channel_layer is not None:
            await self.channel_layer.group_add("emergency_status", self.channel_name)
            self.subscribers[request_id] = {
                "action": action,
                "query_params": kwargs.get("query_params", {}),
            }

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)

    @action()
    async def list(self, **kwargs):
        params = kwargs.get("query_params")
        keys = params.get("keys", [])
        key_ids = await self.get_key_ids(keys)
        if not key_ids:
            return None

        devices = await sync_to_async(list)(self.get_queryset(query_params=params))
        all_data = []

        for device in devices:
            latest_data = await self.get_latest_data(device, key_ids)
            if not latest_data:
                continue

            data_list = [
                {
                    "key_name": telemetry["key"],
                    "ts": telemetry["ts"],
                    "value": telemetry["value"],
                }
                for telemetry in latest_data
            ]

            all_data.append(
                {
                    "device_id": device.id,
                    "room": device.room.number if device and device.room else None,
                    "room_id": str(device.room.id) if device and device.room else None,
                    "data": data_list,
                }
            )

        return all_data, 200

    async def get_latest_activity(self, message, **kwargs):
        entity_id = message.get("entity")
        key = message.get("key")

        for request_id, sub in self.subscribers.items():
            params = sub.get("query_params", {})
            keys = params.get("keys", [])
            delisting_devices = params.get("delisting_devices", [])

            if key not in keys or entity_id in delisting_devices:
                continue

            try:
                device = await sync_to_async(Device.objects.select_related("room").get)(id=entity_id)
            except Device.DoesNotExist:
                continue

            value = (
                message.get("bool_v")
                or message.get("str_v")
                or message.get("long_v")
                or message.get("dbl_v")
                or message.get("json_v")
            )
            result = {
                "device_id": entity_id,
                "room": device.room.number if device.room else None,
                "room_id": str(device.room.id) if device.room else None,
                "data": [
                    {
                        "key_name": key,
                        "ts": message.get("ts"),
                        "value": value if value else None,
                    }
                ],
            }

            await self.reply(data=result, action="update", request_id=request_id)

    @sync_to_async
    def get_key_ids(self, keys):
        return dict(TsKvDictionary.objects.filter(key__in=keys).values_list("key", "key_id"))

    @sync_to_async
    def get_latest_data(self, device, key_ids: dict):
        data = []
        queryset = TsKvLatest.objects.filter(entity=device, key__in=key_ids.values()).values(
            "bool_v", "str_v", "long_v", "dbl_v", "json_v", "key__key", "ts"
        )
        for obj in queryset:
            value = obj.get("bool_v") or obj.get("str_v") or obj.get("long_v") or obj.get("dbl_v") or obj.get("json_v")
            data.append({"key": obj.get("key__key"), "ts": obj.get("ts"), "value": value})
        return data

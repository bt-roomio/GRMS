from asgiref.sync import sync_to_async
from djangochannelsrestframework.observer.generics import action
from djangochannelsrestframework.mixins import ListModelMixin

from main.models import Device
from shuttle.models import TsKvDictionary, TsKvLatest
from shuttle.serializers.emergency_status import EmergencyStatusFilterParams, DeviceTelemetrySerializer
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class EmergencyStatus(ListModelMixin, BaseGenericAsyncAPIConsumer):
    queryset = Device.objects.all()
    serializer_class = DeviceTelemetrySerializer

    async def accept(self, *args, **kwargs):
        self.subscribers = {}
        self.user = self.scope["user"]
        await super().accept(*args, **kwargs)

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        params = EmergencyStatusFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.emergency_status(  # pyright:ignore
            tenant_id=self.user.tenant_id,
            room_types=params.get("room_types"),
            delisting_devices=params.get("delisting_devices"),
        )
        return query

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
                    "device_name": device.name,
                    "room": {
                        "number": device.room.number if device and device.room else None,
                        "id": str(device.room.id) if device and device.room else None,
                    },
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

    @action()
    async def subscribe(self, request_id, action, **kwargs):
        await self.add_group("emergency_status")
        self.subscribers[request_id] = {
            "action": action,
            "query_params": kwargs.get("query_params", {}),
        }

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)

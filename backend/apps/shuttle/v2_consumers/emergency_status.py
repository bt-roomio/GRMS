from asgiref.sync import sync_to_async
from djangochannelsrestframework.observer.generics import action

from main.models import Device
from shuttle.models import TsKvDictionary, TsKvLatest
from shuttle.serializers.emergency_status import DeviceTelemetrySerializer, EmergencyStatusFilterParams
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class EmergencyStatus(BaseGenericAsyncAPIConsumer):
    queryset = Device.objects.all()
    serializer_class = DeviceTelemetrySerializer

    def get_queryset(self, **kwargs):
        query = super().get_queryset(**kwargs)
        params = EmergencyStatusFilterParams.check(data=kwargs.get("query_params", {}))
        query = query.emergency_status(  # pyright:ignore
            tenant_id=self.tenant_id,
            room_types=params.get("room_types"),
            delisting_devices=params.get("delisting_devices"),
        )
        return query

    @action()
    async def list(self, **kwargs):
        params = kwargs.get("query_params")
        data_type = params.get("data_type")
        keys = params.get("keys", [])
        scope = params.get("attribute_scope")
        if not keys:
            return None

        devices = await sync_to_async(list)(self.get_queryset(query_params=params))
        all_data = []

        for device in devices:
            if data_type == "telemetry":
                key_ids = await sync_to_async(self.get_key_ids)(keys)
                if not key_ids:
                    continue
                latest_data = await sync_to_async(self.get_latest_telemetry_data)(device, key_ids)

            else:
                latest_data = await sync_to_async(self.get_latest_attribute_data)(device, keys, scope)

            data_list = [
                {
                    "key_name": item["key"],
                    "ts": item["ts"],
                    "value": item["value"],
                }
                for item in latest_data
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

    def get_key_ids(self, keys):
        return dict(TsKvDictionary.objects.filter(key__in=keys).values_list("key", "key_id"))

    def get_latest_telemetry_data(self, device, key_ids: dict):
        data = []
        queryset = TsKvLatest.objects.filter(entity=device, key__in=key_ids.values()).values(
            "bool_v", "str_v", "long_v", "dbl_v", "json_v", "key__key", "ts"
        )
        for obj in queryset:
            value = self.resolve_value(obj)
            data.append({"key": obj.get("key__key"), "ts": obj.get("ts"), "value": value})
        return data

    def get_latest_attribute_data(self, device, keys, scope):
        data = []
        queryset = device.attribute_kvs.filter(attribute_key__in=keys, attribute_type=scope).values(
            "attribute_key", "last_update_ts", "bool_v", "str_v", "long_v", "dbl_v", "json_v"
        )
        for obj in queryset:
            value = self.resolve_value(obj)
            data.append({"key": obj["attribute_key"], "ts": obj["last_update_ts"], "value": value})
        return data

    @staticmethod
    def resolve_value(obj):
        fields = ["bool_v", "str_v", "dbl_v", "long_v", "json_v"]
        value = next((obj[field] for field in fields if field in obj and obj[field] is not None), None)
        return value

    async def get_latest_activity(self, message, **kwargs):
        updates = message.get("updates", []) or []
        for update in updates:
            await self.handle_activity(update)
        if not updates:
            await self.handle_activity(message.get("update"))

    async def handle_activity(self, message):
        entity_id = message.get("entity")

        for request_id, sub in self.subscribers.items():
            params = sub.get("query_params", {})
            data_type = params.get("data_type", "telemetry")
            keys = params.get("keys", [])
            delisting_devices = params.get("delisting_devices", [])
            scope = params.get("attribute_scope")

            if entity_id in delisting_devices:
                continue

            if data_type == "telemetry":
                await self.handle_telemetry_update(message, keys, entity_id, request_id, sub)
            elif data_type == "attribute":
                await self.handle_attribute_update(message, keys, scope, entity_id, request_id, sub)

    async def handle_telemetry_update(self, message, keys, entity_id, request_id, sub):
        key = message.get("key")
        value = message.get("value")

        if key not in keys:
            return

        try:
            device = await sync_to_async(Device.objects.select_related("room").get)(id=entity_id)
        except Device.DoesNotExist:
            return

        result = {
            "device_id": entity_id,
            "room": device.room.number if device.room else None,
            "room_id": str(device.room.id) if device.room else None,
            "data": [{"key_name": key, "ts": message.get("ts"), "value": value}],
        }
        await self.reply(data=result, action=sub.get("action"), request_id=request_id)

    async def handle_attribute_update(self, message, keys, scope, entity_id, request_id, sub):
        key = message.get("key_name")
        msg_scope = message.get("scope")
        value = message.get("value")

        if key not in keys or scope != msg_scope:
            return

        try:
            device = await sync_to_async(Device.objects.select_related("room").get)(id=entity_id)
        except Device.DoesNotExist:
            return

        result = {
            "device_id": entity_id,
            "room": device.room.number if device.room else None,
            "room_id": str(device.room.id) if device.room else None,
            "data": [{"key_name": key, "ts": message.get("last_update_ts"), "value": value}],
        }
        await self.reply(data=result, action=sub.get("action"), request_id=request_id)

    @action()
    async def subscribe(self, request_id, action, **kwargs):
        await self.add_group(f"emergency_status_{self.tenant_id}")
        self.subscribers[request_id] = {
            "action": action,
            "query_params": kwargs.get("query_params", {}),
        }

    @action()
    async def unsubscribe(self, request_id, **kwargs):
        await self.remove_group(f"emergency_status_{self.tenant_id}")
        self.subscribers.pop(request_id, None)

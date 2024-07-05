import random
from channels.db import database_sync_to_async

from shuttle.utils.get_non_null_field import get_non_null_field
from main.models import Device
from shuttle.models import TsKvDictionary, TsKvLatest
from shuttle.utils.response import response


async def latest_telemetry(cmd, user, send_json):
    result = response({}, cmd.get("cmdId"))
    latest_values = {}

    ts_kv_latest = await get_ts_kv_latest(cmd, user)
    for d in ts_kv_latest:
        ts_kv_dict = await get_ts_kv_dict(d.key)
        field_value = get_non_null_field(d)
        field = field_value[0]
        result["data"][ts_kv_dict.key] = [[d.ts, field_value[1]]]
        latest_values[ts_kv_dict.key] = d.ts
        result["latestValues"] = latest_values

        await fake_change_telemetry(d.id, field)  # This is just for testing purposes

    await send_json(result)


@database_sync_to_async
def fake_change_telemetry(id, field):
    data = TsKvLatest.objects.filter(id=id).first()
    if data:
        setattr(data, field, random.randint(0, 100))
        data.save()


@database_sync_to_async
def get_ts_kv_dict(key_id):
    return TsKvDictionary.objects.filter(key_id=key_id).first()


@database_sync_to_async
def get_ts_kv_latest(cmd, user):
    device = Device.objects.filter(id=cmd.get("entityId"), tenant_id=user.tenant_id).first()
    ts_kv_latest = TsKvLatest.objects.filter(entity_id=device.id if device else None)
    return list(ts_kv_latest)

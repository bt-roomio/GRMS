from channels.db import database_sync_to_async
from core.utils.read_cpu_ram import get_ram_usage
from main.models import Device
from shuttle.models import TsKvDictionary, TsKvLatest
from shuttle.utils.get_non_null_field import get_non_null_field
from shuttle.utils.response import response


async def latest_telemetry(cmd, user, send_json):
    result = response({}, cmd.get("cmdId"))
    latest_values = {}

    ts_kv_latest = await get_ts_kv_latest(cmd, user)
    print(ts_kv_latest)
    for d in ts_kv_latest:
        ts_kv_dict = await get_ts_kv_dict(d.key)
        field, value = get_non_null_field(d)
        # value = await fake_change_telemetry(d.id, field)  # This is just for testing purposes

        result["data"][ts_kv_dict.key] = [[d.ts, value]]
        latest_values[ts_kv_dict.key] = d.ts
        result["latestValues"] = latest_values

    await send_json(result)


@database_sync_to_async
def fake_change_telemetry(id, field):
    data = TsKvLatest.objects.filter(id=id).first()
    value = get_ram_usage()
    if data:
        setattr(data, field, value)
        data.save()
        return value
    return None


@database_sync_to_async
def get_ts_kv_dict(key_id):
    return TsKvDictionary.objects.filter(key_id=key_id).first()


@database_sync_to_async
def get_ts_kv_latest(cmd, user):
    device = Device.objects.filter(id=cmd.get("entityId")).first()
    ts_kv_latest = TsKvLatest.objects.filter(entity_id=device.id if device else None)
    return list(ts_kv_latest)

from channels.db import database_sync_to_async

from shuttle.models import TsKvDictionary, TsKvLatest
from shuttle.utils.get_non_null_field import get_non_null_field
from shuttle.utils.response import response


async def latest_telemetry(cmd, user):
    result = response({}, cmd.get("cmd_id"))
    latest_values = {}

    ts_kv_latest = await get_ts_kv_latest(cmd, user)

    for d in ts_kv_latest:
        ts_kv_dict = await database_sync_to_async(get_ts_kv_dict)(d.key)
        _, value = get_non_null_field(d)

        result["data"][ts_kv_dict.key] = [[d.ts, value]]
        latest_values[ts_kv_dict.key] = d.ts
        result["latestValues"] = latest_values

    return result


def get_ts_kv_dict(key_id):
    return TsKvDictionary.objects.filter(key_id=key_id).first()


@database_sync_to_async
def get_ts_kv_latest(cmd, user):
    ts_kv_latest = TsKvLatest.objects.filter(entity_id=cmd.get("entity_id"), entity__tenant=user.tenant)
    return list(ts_kv_latest)

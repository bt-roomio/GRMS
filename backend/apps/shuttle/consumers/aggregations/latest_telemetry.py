from channels.db import database_sync_to_async
from django.db.models import F

from shuttle.models import TsKvDictionary, TsKvLatest
from shuttle.utils.response import response


async def latest_telemetry(cmd, user):
    result = response({}, cmd.get("cmd_id"))
    latest_values = {}

    try:
        ts_kv_latest = await get_ts_kv_latest(cmd, user)

        for d in ts_kv_latest:
            ts, value, key = d.values()

            result["data"][key] = [[ts, value]]
            latest_values[key] = ts
            result["latestValues"] = latest_values
    except Exception as err:
        result["error_code"] = 400
        result["error_msg"] = str(err)
    finally:
        return result


def get_ts_kv_dict(key_id):
    return TsKvDictionary.objects.filter(key_id=key_id).first()


@database_sync_to_async
def get_ts_kv_latest(cmd, user):
    data = (
        TsKvLatest.objects.select_related("key")
        .filter(entity_id=cmd.get("entity_id"), entity__tenant=user.tenant)
        .annotate(key_name=F("key__key"))
        .values("ts", "str_v", "bool_v", "json_v", "long_v", "dbl_v", "key_name")
    )
    cleaned_data = [{k: v for k, v in record.items() if v is not None} for record in data]
    return cleaned_data

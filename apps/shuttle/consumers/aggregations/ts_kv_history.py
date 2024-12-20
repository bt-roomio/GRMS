import time

from channels.consumer import database_sync_to_async

from shuttle.models import TsKv, TsKvDictionary
from shuttle.utils.camel_to_snake import camel_to_snake
from shuttle.utils.response import response


async def history_ts_kv(cmd, user):
    result = response({}, cmd.get("cmd_id"))
    history_cmd = {camel_to_snake(k): v for k, v in cmd.get("history_cmd", {}).items()}
    data, count_of_data = await ts_kv_history(user, entity_id=cmd.get("entity_id"), **history_cmd)

    del result["data"]
    result["update"] = data
    result["allowedEntities"] = count_of_data
    result["cmdUpdateType"] = "ENTITY_DATA"
    return result


@database_sync_to_async
def ts_kv_history(user, keys, start_ts, interval, agg, limit, entity_id, end_ts=None, *args, **kwargs):
    end_ts = int(time.time() * 1000) if not end_ts else end_ts
    data, count_of_data = TsKv.objects.filter(entity__tenant_id=user.tenant_id, entity_id=entity_id).get_history(
        keys, start_ts, end_ts, interval, agg, limit
    )
    return data, count_of_data


def get_ts_kv_dict_ids(keys):
    return TsKvDictionary.objects.filter(key__in=keys).values("key_id", "key")

from channels.consumer import database_sync_to_async
from shuttle.models import TsKv, TsKvDictionary
from shuttle.utils.camel_to_snake import camel_to_snake


async def history_ts_kv(cmd, user):
    avail_parameters = ["keys", "start_ts", "end_ts", "interval", "agg", "limit"]
    history_cmd = {camel_to_snake(k): v for k, v in cmd.get("historyCmd", {}).items()}
    history_cmd = {k: v for k, v in history_cmd.items() if k in avail_parameters}

    data = await ts_kv_history(user, **history_cmd)
    return data


@database_sync_to_async
def ts_kv_history(user, keys, start_ts, end_ts, interval, agg, limit):
    data = TsKv.objects.filter(entity__tenant_id=user.tenant_id).get_history(
        keys, start_ts, end_ts, interval, agg, limit
    )
    return data


def get_ts_kv_dict_ids(keys):
    return TsKvDictionary.objects.filter(key__in=keys).values("key_id", "key")

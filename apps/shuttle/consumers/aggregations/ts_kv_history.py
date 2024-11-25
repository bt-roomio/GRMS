import math

from channels.consumer import database_sync_to_async
from django.db.models import Avg, ExpressionWrapper, F, IntegerField, Min
from django.db.models.functions import Floor
from shuttle.models import TsKv, TsKvDictionary


@database_sync_to_async
def ts_kv_history(start_ts, end_ts, interval, keys, limit):
    # Annotate and filter the queryset
    filtered_data = TsKv.objects.filter(ts__gte=start_ts, ts__lte=end_ts, key__in=keys).annotate(
        grp=Floor(ExpressionWrapper((F("ts") - start_ts) / interval, output_field=IntegerField()))
    )
    length_of_data_in_one = math.floor(len(filtered_data) / limit)

    # Group by 'grp' and annotate with 'start_ts' and 'avg_value'
    grouped_data = (
        filtered_data.values("grp").annotate(start_ts=Min("ts"), avg_value=Avg("long_v")).order_by("start_ts")[:limit]
    )

    return [
        {"ts": entry["start_ts"], "value": entry["avg_value"], "count": length_of_data_in_one} for entry in grouped_data
    ]


async def history_telemetry(cmd):
    history = cmd.get("historyCmd")
    start_ts = history.get("startTs")
    end_ts = history.get("endTs")
    limit = history.get("limit")
    interval = history.get("interval")
    keys = await database_sync_to_async(get_ts_kv_dict_ids)(history.get("keys"))
    return await ts_kv_history(start_ts, end_ts, interval, keys, limit)


def get_ts_kv_dict_ids(keys):
    return list(TsKvDictionary.objects.filter(key__in=keys).values_list("key_id", flat=True))


@database_sync_to_async
def get_ts_kv(start_ts, end_ts, keys):
    query = TsKv.objects.filter(ts__gte=start_ts, ts__lte=end_ts, key__in=keys)
    return list(query)

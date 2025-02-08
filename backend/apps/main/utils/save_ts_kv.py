from core.utils.get_time import get_mil_sec
from shuttle.models import TsKv, TsKvDictionary, TsKvLatest
from shuttle.utils.find_compatible_field import find_compatible_field


def save_telemetry_kv(devices, data):
    telemetry = {}
    for key, item in find_compatible_field(data).items():
        fields = {"bool_v": None, "str_v": None, "long_v": None, "dbl_v": None, "json_v": None}
        ts_kv_dict, _ = TsKvDictionary.objects.get_or_create(key=key)
        fields[item[0]] = item[1]
        ts_kvs = TsKv.objects.filter(entity__in=devices, key=ts_kv_dict.key_id)
        for ts_kv in ts_kvs:
            for k, v in fields.items():
                setattr(ts_kv, k, v)
            ts_kv.save()
            telemetry[str(ts_kv.entity_id)] = {key: item[1]}

        ts_kvs_latest = TsKvLatest.objects.filter(entity__in=devices, key=ts_kv_dict.key_id)
        for ts_kv_latest in ts_kvs_latest:
            for k, v in fields.items():
                setattr(ts_kv_latest, k, v)
            ts_kv_latest.ts = get_mil_sec()
            ts_kv_latest.save()

    return telemetry

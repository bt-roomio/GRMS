from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField, IntegerField, Q, TextField, Window
from django.db.models.functions import Cast, Coalesce, Floor, Lag, Round

from core.querysets.base_queryset import BaseQuerySet
from core.utils.aggregation_func import AGGREGATION_FUNCTIONS


class TsKvQuerySet(BaseQuerySet):
    def get_entity_ts_kv(self, entity):
        return self.filter(entity=entity)

    def get_history_v2(self, keys, start_ts, end_ts, interval=10, agg="Avg", limit=100):
        agg_function = AGGREGATION_FUNCTIONS.get(agg, Avg)
        keys = self.get_ts_kv_type_of_field_and_key_id(keys)
        result = {item["key"]: [] for item in keys}
        count_of_data = 0

        for key_item in keys:
            query = self.filter(ts__gte=start_ts, ts__lte=end_ts, key=key_item["key_id"])

            if key_item["type"] in ["dbl_v", "long_v"]:
                query = (
                    query.annotate(
                        interval_time=Floor(
                            ExpressionWrapper(
                                (F("ts") / interval) * interval,
                                output_field=IntegerField(),
                            )
                        ),
                        avail_field=Coalesce(F("dbl_v"), F("long_v"), output_field=FloatField()),
                    )
                    .values("key", "interval_time")
                    .annotate(count_per_group=Count("avail_field"))
                    .filter(count_per_group__gte=1)
                    .order_by("-key", "-interval_time")
                )
                if agg_function not in [None, "Change"]:
                    query = query.annotate(aggreagted_field=Round(agg_function(F("avail_field")), precision=2))
                    query = query.annotate(ts=F("interval_time"), value=F("aggreagted_field")).values("ts", "value")
                else:
                    query = query.annotate(ts=F("interval_time"), value=F("avail_field")).values("ts", "value")

                result[key_item["key"]] = list(query[:limit])
                count_of_data += query.count()

            elif key_item["type"] in ["json_v", "str_v", "bool_v"]:
                query = (
                    query.annotate(
                        interval_time=F("ts"),
                        avail_field=Coalesce(
                            Cast("json_v", TextField()),
                            Cast("bool_v", TextField()),
                            F("str_v"),
                            output_field=TextField(),
                        ),
                    )
                    .values("key", "interval_time", "avail_field")
                    .annotate(ts=F("interval_time"), value=F("avail_field"))
                    .values("ts", "value")
                    .order_by("-ts")
                )

                result[key_item["key"]] = list(query[:limit])
                count_of_data += query.count()

        return result

    def get_history(self, keys, start_ts, end_ts, interval=10, agg="Avg", limit=100):
        agg_function = AGGREGATION_FUNCTIONS.get(agg, Avg)
        keys = self.get_ts_kv_type_of_field_and_key_id(keys)
        result = {item["key"]: [] for item in keys}
        count_of_data = 0

        for key_item in keys:
            query = self.filter(ts__gte=start_ts, ts__lte=end_ts, key=key_item["key_id"])
            if key_item["type"] in ["dbl_v", "long_v"] and agg_function == "Change":
                query = (
                    query.annotate(prev_value=Window(expression=Lag(key_item["type"]), order_by=F("ts").desc()))
                    .filter(Q(prev_value__isnull=True) | ~Q(dbl_v=F("prev_value")))
                    .values("ts", values=F(key_item["type"]))
                )
                result[key_item["key"]] = list(query[:limit])
                count_of_data += query.count()

            elif key_item["type"] in ["dbl_v", "long_v"] and agg_function != "Change":
                query = (
                    query.annotate(
                        interval_time=Floor(
                            ExpressionWrapper(
                                (F("ts") / interval) * interval,
                                output_field=IntegerField(),
                            )
                        ),
                        avail_field=Coalesce(F("dbl_v"), F("long_v"), output_field=FloatField()),
                    )
                    .values("key", "interval_time")
                    .annotate(count_per_group=Count("avail_field"))
                    .filter(count_per_group__gt=1)
                    .order_by("-key", "-interval_time")
                )
                if agg_function is not None:
                    query = query.annotate(aggreagted_field=Round(agg_function(F("avail_field")), precision=2))
                    query = query.annotate(ts=F("interval_time"), value=F("aggreagted_field")).values("ts", "value")
                else:
                    query = query.annotate(ts=F("interval_time"), value=F("avail_field")).values("ts", "value")

                result[key_item["key"]] = list(query[:limit])
                count_of_data += query.count()

            elif key_item["type"] in ["json_v", "str_v", "bool_v"]:
                query = (
                    query.annotate(
                        interval_time=F("ts"),
                        avail_field=Coalesce(
                            Cast("json_v", TextField()),
                            Cast("bool_v", TextField()),
                            F("str_v"),
                            output_field=TextField(),
                        ),
                    )
                    .values("key", "interval_time", "avail_field")
                    .annotate(ts=F("interval_time"), value=F("avail_field"))
                    .values("ts", "value")
                    .order_by("-ts", "-interval_time")
                )

                result[key_item["key"]] = list(query[:limit])
                count_of_data += query.count()

        return result, count_of_data

    def get_ts_kv_type_of_field_and_key_id(self, keys):
        from shuttle.consumers.aggregations.ts_kv_history import get_ts_kv_dict_ids
        from shuttle.utils.get_non_null_field import get_non_null_field

        ts_kv_dict = get_ts_kv_dict_ids(keys)
        for item in ts_kv_dict:
            instance = self.filter(key=item.get("key_id")).first()
            field_type, _ = get_non_null_field(instance)
            item["type"] = field_type

        return list(ts_kv_dict)

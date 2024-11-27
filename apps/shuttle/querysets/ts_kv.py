from core.querysets.base_queryset import BaseQuerySet
from core.utils.aggregation_func import AGGREGATION_FUNCTIONS
from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField, IntegerField, TextField
from django.db.models.functions import Cast, Coalesce, Floor, Round


class TsKvQuerySet(BaseQuerySet):
    def get_entity_ts_kv(self, entity):
        return self.filter(entity=entity)

    def get_history(self, keys, start_ts, end_ts, interval=10, agg="Avg", limit=100):
        agg_function = AGGREGATION_FUNCTIONS.get(agg, Avg)
        keys = self.get_ts_kv_type_of_field_and_key_id(keys)
        result = []

        for key_item in keys:
            query = self.filter(ts__gte=start_ts, ts__lte=end_ts, key=key_item["key_id"])
            if key_item["type"] in ["dbl_v", "long_v"]:
                query = (
                    query.annotate(
                        interval_time=Floor(
                            ExpressionWrapper((F("ts") / interval) * interval, output_field=IntegerField())
                        ),
                        avail_field=Coalesce(F("dbl_v"), F("long_v"), output_field=FloatField()),
                    )
                    .values("key", "interval_time")
                    .annotate(count_per_group=Count("avail_field"))
                    .filter(count_per_group__gt=1)
                    .order_by("key", "interval_time")
                )
                if agg_function is not None:
                    query = query.annotate(aggreagted_field=Round(agg_function(F("avail_field")), precision=2))
                result.extend(query[:limit])

            if key_item["type"] in ["json_v", "str_v", "bool_v"]:
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
                    .order_by("key", "interval_time")
                )
                result.extend(query[:limit])

        return result

    def get_ts_kv_type_of_field_and_key_id(self, keys):
        from shuttle.consumers.aggregations.ts_kv_history import get_ts_kv_dict_ids
        from shuttle.utils.get_non_null_field import get_non_null_field

        ts_kv_dict = get_ts_kv_dict_ids(keys)
        for item in ts_kv_dict:
            instance = self.filter(key=item.get("key_id")).first()
            field_type, _ = get_non_null_field(instance)
            item["type"] = field_type

        return list(ts_kv_dict)

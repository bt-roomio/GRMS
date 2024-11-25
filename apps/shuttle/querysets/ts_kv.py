from core.querysets.base_queryset import BaseQuerySet


class TsKvQuerySet(BaseQuerySet):
    def get_entity_ts_kv(self, entity):
        return self.filter(entity=entity)

    def get_history(self, keys, start_ts, end_ts, interval, agg, limit):
        from core.utils.aggregation_func import AGGREGATION_FUNCTIONS
        from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField, IntegerField
        from django.db.models.functions import Coalesce, Floor
        from shuttle.consumers.aggregations.ts_kv_history import get_ts_kv_dict_ids

        agg_function = AGGREGATION_FUNCTIONS.get(agg, Avg)
        key_ids = get_ts_kv_dict_ids(keys)
        query = self.filter(ts__gte=start_ts, ts__lte=end_ts, key__in=key_ids)
        query = (
            query.annotate(
                interval_time=Floor(ExpressionWrapper((F("ts") / interval) * interval, output_field=IntegerField())),
                avail_field=Coalesce(F("dbl_v"), F("long_v"), output_field=FloatField()),
            )
            .values("key", "interval_time")
            .annotate(count_per_group=Count("avail_field"))
            .filter(count_per_group__gt=1)
            .order_by("key", "interval_time")
        )
        if agg_function is not None:
            query = query.annotate(aggregated_value=agg_function("avail_field"))

        return query

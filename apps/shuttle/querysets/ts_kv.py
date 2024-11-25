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
                interval_time=Func(
                    ExpressionWrapper((F("ts") / interval) * interval, output_field=FloatField()),
                    function="FLOOR",
                    output_field=IntegerField(),
                ),
                aggregated_value=agg_function(Coalesce(F("dbl_v"), F("long_v"), output_field=FloatField())),
                field_value=Coalesce(
                    Cast(F("json_v"), TextField()),
                    Cast(F("bool_v"), TextField()),
                    F("str_v"),
                    output_field=TextField(),
                ),
            )
            .values("key", "interval_time", "field_value")
            .order_by("key", "interval_time")
        )

        return query


"""
Raw query for historiy data
SELECT
	"shuttle_ts_kv"."key",
	FLOOR(("shuttle_ts_kv"."ts" / 24) * 24) AS "interval_time",
	AVG(COALESCE("shuttle_ts_kv"."dbl_v", "shuttle_ts_kv"."long_v")) AS "aggregated_value",
	COALESCE(("shuttle_ts_kv"."json_v")::text, ("shuttle_ts_kv"."bool_v")::text, "shuttle_ts_kv"."str_v") AS "field_value"
FROM
	"shuttle_ts_kv"
WHERE
	"shuttle_ts_kv"."entity_id" IN ('9829490d-f742-400e-8f38-aae5155e0b27') -- '4b6ab65b-8cc5-44f3-b45c-312d5254cb86'
	AND "shuttle_ts_kv"."key" IN (3)
	AND "shuttle_ts_kv"."ts" >= 1732123722
	AND "shuttle_ts_kv"."ts" <= 1732123794
GROUP BY
	"shuttle_ts_kv"."key",
	FLOOR(("shuttle_ts_kv"."ts" / 24) * 24),
	COALESCE(("shuttle_ts_kv"."json_v")::text, ("shuttle_ts_kv"."bool_v")::text, "shuttle_ts_kv"."str_v")
ORDER BY
	"shuttle_ts_kv"."key" ASC,
	"interval_time" ASC;
"""

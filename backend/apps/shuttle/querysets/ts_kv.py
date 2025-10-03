from datetime import datetime
from django.utils import timezone

from django.db.models import (
    Avg,
    CharField,
    Count,
    DateTimeField,
    ExpressionWrapper,
    F,
    FloatField,
    Func,
    IntegerField,
    Q,
    Sum,
    TextField,
    Value,
    Window,
)
from django.db.models.functions import Cast, Coalesce, Floor, Lag, Round
from django.utils import timezone

from core.querysets.base_queryset import BaseQuerySet
from core.utils.aggregation_func import AGGREGATION_FUNCTIONS, make_interval
from shuttle.utils.datetime_aware import to_datetime_aware
from shuttle.utils.fill_empty_intervals import fill_missing_intervals


class TsKvQuerySet(BaseQuerySet):
    def by_tenant(self, tenant):
        return self.filter(entity__tenant=tenant)

    def by_device(self, entity):
        return self.filter(entity=entity)

    def gateway_logs(self, entity, key, start_ts, end_ts, sort_by=[]):
        query = self.by_device(entity)
        query = query.filter(ts__gte=start_ts, key__key=key)
        query = query.filter(ts__lte=end_ts) if end_ts else query
        query = (
            query.annotate(
                key_name=F("key__key"),
                value=Coalesce("str_v", Cast("json_v", output_field=CharField()), output_field=CharField()),
            )
            .values("ts", "key_name", "value")
            .order_by(*sort_by)
        )

        return query

    def tag_logs(self, entity, keys, start_ts, all_tags, end_ts=None, sort_by=None):
        if sort_by is None:
            sort_by = ["-ts"]

        # Base queryset: filter early and include select_related for join optimizations.
        qs = self.select_related("key").by_device(entity).filter(ts__gte=start_ts)
        qs = qs.filter(ts__lte=end_ts) if end_ts else qs
        qs = qs.filter(key__key__in=keys) if not all_tags else qs
        qs = qs.annotate(
            prev_dbl_v=Window(
                expression=Lag("dbl_v"),
                partition_by=F("key__key"),
                order_by=F("ts").asc(),
            ),
            prev_json_v=Window(
                expression=Lag("json_v"),
                partition_by=F("key__key"),
                order_by=F("ts").asc(),
            ),
            prev_long_v=Window(
                expression=Lag("long_v"),
                partition_by=F("key__key"),
                order_by=F("ts").asc(),
            ),
            prev_str_v=Window(
                expression=Lag("str_v"),
                partition_by=F("key__key"),
                order_by=F("ts").asc(),
            ),
            prev_bool_v=Window(
                expression=Lag("bool_v"),
                partition_by=F("key__key"),
                order_by=F("ts").asc(),
            ),
            key_name=F("key__key"),
            value=Coalesce(
                Cast(F("dbl_v"), output_field=CharField()),
                Cast(F("long_v"), output_field=CharField()),
                F("str_v"),
                Cast(F("bool_v"), output_field=CharField()),
                Cast(F("json_v"), output_field=CharField()),
                output_field=CharField(),
            ),
        )

        # Dynamically build filter conditions for detecting change in values.
        filter_conditions = Q()
        for field in ["dbl_v", "json_v", "long_v", "str_v", "bool_v"]:
            filter_conditions &= Q(**{f"prev_{field}__isnull": True}) | ~Q(**{field: F(f"prev_{field}")})

        qs = qs.filter(filter_conditions).values("ts", "key_name", "value").order_by(*sort_by)
        return qs

    def get_history_v2(self, keys, start_ts, interval, agg, limit, sort_by, auto_fill):
        origin_dt = Value(start_ts, output_field=DateTimeField())
        sort_by = ["interval_ts"] if sort_by is None else sort_by
        agg_function = AGGREGATION_FUNCTIONS.get(agg, Avg)
        interval = make_interval(*interval.split(" ")) if interval and len(interval.split(" ")) > 1 else interval
        limit = limit or 100
        agg_function = Avg if agg in ["Change", None] else agg_function
        sum_expr = Sum("avail_field", output_field=FloatField())
        count_expr = Count("interval_ts")

        avg_expr = ExpressionWrapper(sum_expr / count_expr, output_field=FloatField())

        result = {}

        for key in keys:
            query = self.filter(key__key=key, **({"ts__gte": start_ts} if start_ts else {}))

            last_known = None
            if (
                datetime.strptime(start_ts, "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S") == "00:00:00"
                and limit == 720
                and interval == "2 minute"
            ):
                st = to_datetime_aware(start_ts)
                has_value = self.filter(key__key=key, ts__gte=st)
                if not has_value:
                    last_known = self.filter(key__key=key, ts__lt=start_ts).order_by("-ts").first()
                    if last_known:
                        query = self.filter(key__key=key, ts=last_known.ts)
                        origin_dt = Value(last_known.ts, output_field=DateTimeField())

            if interval in ["month", "year"]:
                query = query.annotate(
                    interval_ts=Func(
                        Value(interval),  # bin width
                        F("ts"),  # timestamp field
                        function="date_trunc",
                        output_field=DateTimeField(),
                    ),
                    avail_field=Coalesce(F("dbl_v"), F("long_v"), output_field=FloatField()),
                )
            elif interval is None:
                query = query.annotate(
                    interval_ts=F("ts"),
                    avail_field=Coalesce(
                        F("str_v"),
                        Cast("json_v", output_field=TextField()),
                        Cast("bool_v", output_field=TextField()),
                        output_field=CharField(),
                    ),
                )
            else:
                query = query.annotate(
                    interval_ts=Func(
                        Value(interval),  # bin width
                        F("ts"),  # timestamp field
                        origin_dt,
                        function="date_bin",
                        output_field=DateTimeField(),
                    ),
                    avail_field=Coalesce(F("dbl_v"), F("long_v"), output_field=FloatField()),
                )

            data = (
                query.values("interval_ts")
                .annotate(
                    value=Round(avg_expr, precision=2),
                    ts=F("interval_ts"),
                    key_name=F("key__key"),
                    count=count_expr,
                )
                .values("value", "ts", "key_name", "count")[:limit]
            )

            if auto_fill:
                data = fill_missing_intervals(
                    data,
                    interval,
                    start_ts,
                    limit,
                    key_name=key,
                )

            if "-interval_ts" in sort_by:
                data = sorted(data, key=lambda d: d["ts"], reverse=True)
            data = [item for item in data if item["ts"] <= timezone.now()]

            result[key] = data
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

    def tenant_avg_history(
            self,
            tenant,
            keys,
            start_ts,
            interval=None,
            limit=100,
            sort_by=None,
            end_ts=None,
            room_field="entity__room_id",
    ):
        sort_by = sort_by or ["interval_ts"]
        if isinstance(start_ts, str):
            start_ts = datetime.strptime(start_ts, "%Y-%m-%d %H:%M:%S")
        if isinstance(end_ts, str):
            end_ts = datetime.strptime(end_ts, "%Y-%m-%d %H:%M:%S")

        norm_interval = make_interval(*interval.split(" ")) if interval and len(interval.split(" ")) > 1 else interval
        tenant_filter = {"entity__tenant": tenant} if hasattr(tenant, "id") else {"entity__tenant_id": tenant}
        origin_dt = Value(start_ts, output_field=DateTimeField())
        effective_end = timezone.now()


        def bucket(qs):
            if norm_interval in ["month", "year"]:
                return qs.annotate(
                    interval_ts=Func(Value(norm_interval), F("ts"), function="date_trunc",
                                     output_field=DateTimeField()),
                    avail_field=Coalesce(F("dbl_v"), F("long_v"), output_field=FloatField()),
                )
            if norm_interval is None:
                return qs.annotate(
                    interval_ts=F("ts"),
                    avail_field=Coalesce(F("dbl_v"), F("long_v"), output_field=FloatField()),
                )
            return qs.annotate(
                interval_ts=Func(Value(norm_interval), F("ts"), origin_dt, function="date_bin",
                                 output_field=DateTimeField()),
                avail_field=Coalesce(F("dbl_v"), F("long_v"), output_field=FloatField()),
            )

        def per_key_stats(key):
            base = self.filter(**tenant_filter, key__key=key)
            if start_ts: base = base.filter(ts__gte=start_ts)
            if end_ts:   base = base.filter(ts__lte=end_ts)

            rows = list(
                bucket(base)
                .values("interval_ts", room_field)
                .annotate(room_value=Avg("avail_field"), room_count=Count("*"))
                .order_by(room_field, "interval_ts")
            )

            if not rows:
                filled = fill_missing_intervals([], norm_interval, start_ts, limit, key_name=key, end_ts=effective_end)
                out = []
                for r in filled:
                    out.append({
                        "ts": r["ts"],
                        "key_name": key,
                        "value": {"avg": r["value"], "min": r["value"], "max": r["value"]},
                        "count": 0,
                    })
                if "-interval_ts" in sort_by:
                    out.reverse()
                return out

            per_room = {}
            for r in rows:
                rid = r[room_field]
                per_room.setdefault(rid, []).append(
                    {"ts": r["interval_ts"], "value": r["room_value"], "count": r["room_count"], "key_name": key}
                )

            filled = {
                rid: fill_missing_intervals(series, norm_interval, start_ts, limit, key_name=key, end_ts=effective_end)
                for rid, series in per_room.items()
            }

            canon = next(iter(filled.values()))
            room_ids = list(filled.keys())
            n_rooms = len(room_ids)

            out = []
            for i in range(len(canon)):
                vals = [filled[r][i]["value"] for r in room_ids]
                avg_v = round(sum(vals) / n_rooms, 2) if n_rooms else 0.0
                min_v = round(min(vals), 2) if n_rooms else 0.0
                max_v = round(max(vals), 2) if n_rooms else 0.0
                out.append({
                    "ts": canon[i]["ts"],
                    "key_name": key,
                    "value": {"avg": avg_v, "min": min_v, "max": max_v},
                    "count": n_rooms,
                })

            if "-interval_ts" in sort_by:
                out.reverse()
            return out[:limit]

        return {key: per_key_stats(key) for key in keys}

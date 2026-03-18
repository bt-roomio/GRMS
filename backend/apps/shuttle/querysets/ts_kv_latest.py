from typing import List

from django.db.models import CharField, F, Q, Count
from django.db.models.functions import Cast, Coalesce

from core.querysets.base_queryset import BaseQuerySet


class TsKvLatestQuerySet(BaseQuerySet):
    def by_tenant(self, tenant):
        return self.filter(entity__tenant=tenant)

    def by_device(self, entity):
        return self.filter(entity=entity)

    def get_entity(self, entity):
        return self.filter(entity=entity)

    def get_by_keys(self, keys=List[str]):
        from shuttle.models import TsKvDictionary

        key_ids = TsKvDictionary.objects.get_key_ids(keys)  # pyright: ignore
        return self.filter(key__in=key_ids)

    def get_ts_kv_latest(self, entity, tenant, sort_by=[]):
        query = (
            self.select_related("key")
            .by_tenant(tenant)
            .by_device(entity)
            .annotate(
                key_name=F("key__key"),
                value=Coalesce(
                    Cast("bool_v", output_field=CharField()),
                    Cast("str_v", output_field=CharField()),
                    Cast("long_v", output_field=CharField()),
                    Cast("dbl_v", output_field=CharField()),
                    Cast("json_v", output_field=CharField()),
                    output_field=CharField(),
                ),
            )
            .values("ts", "key_name", "value")
            .order_by(*sort_by)
        )
        return query

    def unique_keys_by_tenant(self, tenant_id):
        return self.filter(entity__tenant_id=tenant_id).values_list("key__key", flat=True).distinct().order_by("key__key")

    def room_flag_counts(self, tenant_id):
        alias = {"DND Relay": "dnd", "MUR Relay": "mur", "Occupancy State": "occupied", "AC ON OFF": "ac-on-off"}
        rows = (
            self.filter(
                entity__tenant_id=tenant_id,
                entity__room__isnull=False,
                key__key__in=alias.keys(),
            )
            .filter(Q(long_v=1) | Q(bool_v=True))
            .values("key__key")
            .annotate(count=Count("entity__room_id", distinct=True))
        )

        out = {v: 0 for v in alias.values()}
        out.update({alias[r["key__key"]]: r["count"] for r in rows})
        return out

from typing import List

from django.db.models import CharField, F
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

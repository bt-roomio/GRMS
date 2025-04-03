from typing import List

from django.db.models import F

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
            .by_device(entity)
            .by_tenant(tenant)
            .annotate(key_name=F("key__key"))
            .values("ts", "str_v", "bool_v", "json_v", "long_v", "dbl_v", "key_name")
            .order_by(*sort_by)
        )

        cleaned_data = [{k: v for k, v in record.items() if v is not None} for record in query]
        cleaned_data = [
            {(k if k in ["ts", "key_name"] else "value"): v for k, v in record.items()} for record in cleaned_data
        ]
        return cleaned_data

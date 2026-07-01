from typing import List

from django.db.models import CharField, Count, F, Q
from django.db.models.functions import Cast, Coalesce

from core.querysets.base_queryset import BaseQuerySet


class TsKvLatestQuerySet(BaseQuerySet):
    VALUE_FIELDS = ("bool_v", "str_v", "long_v", "dbl_v", "json_v")

    @classmethod
    def _value_expr(cls):
        """First non-null typed column, cast to text (matches telemetry's string contract)."""
        return Coalesce(
            *(Cast(field, output_field=CharField()) for field in cls.VALUE_FIELDS),
            output_field=CharField(),
        )

    def by_tenant(self, tenant):
        return self.filter(entity__tenant=tenant)

    def by_device(self, entity):
        return self.filter(entity=entity)

    def get_entity(self, entity):
        return self.filter(entity=entity)

    def get_by_keys(self, keys=List[str]):
        from shuttle.models import TsKvDictionary

        key_ids = TsKvDictionary.objects.get_key_ids(keys)
        return self.filter(key__in=key_ids)

    def get_ts_kv_latest(self, entity, tenant, sort_by=[]):
        query = (
            self.select_related("key")
            .by_tenant(tenant)
            .by_device(entity)
            .annotate(key_name=F("key__key"), value=self._value_expr())
            .values("ts", "key_name", "value")
            .order_by(*sort_by)
        )
        return query

    def get_ts_kv_latest_by_room(self, room, tenant, sort_by=()):
        return (
            self.filter(entity__room=room, entity__tenant=tenant)
            .values("ts", "id", "key__key", *self.VALUE_FIELDS)
            .order_by(*sort_by)
        )

    def unique_keys_by_tenant(self, tenant_id, tag_name: str | None = None):
        query = self.filter(key__key__icontains=tag_name) if tag_name else self
        query = query.filter(entity__tenant_id=tenant_id).values_list("key__key", flat=True).distinct()

        return query.order_by("key__key")

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

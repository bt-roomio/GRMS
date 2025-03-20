from typing import List

from core.querysets.base_queryset import BaseQuerySet


class TsKvLatestQuerySet(BaseQuerySet):

    def get_entity(self, entity):
        return self.filter(entity=entity)

    def get_by_keys(self, keys=List[str]):
        from shuttle.models import TsKvDictionary

        key_ids = TsKvDictionary.objects.get_key_ids(keys)  # pyright: ignore
        return self.filter(key__in=key_ids)

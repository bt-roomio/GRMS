from core.querysets.base_queryset import BaseQuerySet


class TsKvDictionaryQuerySet(BaseQuerySet):
    def get_key_ids(self, keys=None):
        if keys is None:
            keys = []
        return self.filter(key__in=keys).values_list("key_id", flat=True)

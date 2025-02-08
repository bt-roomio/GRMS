from core.querysets.base_queryset import BaseQuerySet


class TsKvDictionaryQuerySet(BaseQuerySet):
    def get_key_ids(self, keys=None):
        if keys is None:
            keys = []
        return self.filter(key__in=keys).values_list("key_id", flat=True)

    def get_key_id(self, key):
        query = self.filter(key=key).first()
        return query and query.key_id

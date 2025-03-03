from core.querysets.base_queryset import BaseQuerySet


class RelationQuerySet(BaseQuerySet):
    def list(self, tenant, from_id=None, to_id=None):
        query = (
            self.select_related("from_id").filter(
                from_id__tenant=tenant,
                from_id__is_active=True,
                from_id=from_id,
            )
            if from_id
            else self.none()
        )
        query = (
            self.select_related("to_id").filter(
                to_id__tenant=tenant,
                to_id__is_active=True,
                to_id=to_id,
            )
            if to_id
            else query
        )
        return query

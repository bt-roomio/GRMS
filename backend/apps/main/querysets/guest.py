from core.querysets.base_queryset import BaseQuerySet


class GuestQuerySet(BaseQuerySet):
    def list(self, tenant_id, room=None):
        query = self.filter(tenant_id=tenant_id)
        query = query.filter(room=room, is_active=True) if room else query
        return query

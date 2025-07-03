from django.db.models import Exists, OuterRef

from core.querysets.base_queryset import BaseQuerySet


class GuestCardQuerySet(BaseQuerySet):
    def list(self, tenant_id, room=None, sort_by=[]):
        query = self.filter(guest__tenant_id=tenant_id, is_active=True)
        query = query.filter(guest__room=room) if room else query
        return query.order_by(*sort_by)

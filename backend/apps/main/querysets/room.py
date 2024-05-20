from django.db.models import Q
from core.querysets.base_queryset import BaseQuerySet


class RoomQuerySet(BaseQuerySet):
    def list(self, tenant, status, search=None):
        query = self.filter(active=True)
        query = query.filter(status=status, tenant=tenant)
        query = query.filter(Q(room_number=search) | Q(floor=search) | Q(block=search)) if search else query
        return query

from core.querysets.base_queryset import BaseQuerySet


class RoomTypeQuerySet(BaseQuerySet):
    def list(self, tenant, search=None):
        query = self.filter(tenant=tenant)
        query = query.filter(title__icontains=search) if search else query

        return query.order_by("created_at")

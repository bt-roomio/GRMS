from core.querysets.base_queryset import BaseQuerySet


class RoomQuerySet(BaseQuerySet):
    def by_tenant(self, tenant):
        return self.filter(active=True, tenant=tenant)

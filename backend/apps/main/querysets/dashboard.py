from core.querysets.base_queryset import BaseQuerySet


class DashboardQuerySet(BaseQuerySet):
    def list(self, tenant_id, sort_by=[]):
        query = self.prefetch_related("room_types").filter(tenant_id=tenant_id)
        return query.order_by(*sort_by)

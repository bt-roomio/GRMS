from core.querysets.base_queryset import BaseQuerySet


class DeviceQuerySet(BaseQuerySet):
    def list(self, tenant, search=None, status=None, sort_by=None):
        query = self.filter(tenant=tenant, is_active=True)
        query = query.filter(name__icontains=search) if search else query
        query = query.filter(status=status) if status is not None else query
        query = query.order_by(*sort_by) if sort_by else query

        return query

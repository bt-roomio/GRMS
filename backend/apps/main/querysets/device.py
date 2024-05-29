from core.querysets.base_queryset import BaseQuerySet


class DeviceQuerySet(BaseQuerySet):
    def list(self, tenant, search=None):
        query = self.filter(tenant=tenant)
        query = query.filter(name__icontains=search) if search else query
        print(search)
        return query

from core.querysets.base_queryset import BaseQuerySet


class TagTypeGroupQuerySet(BaseQuerySet):
    def by_tenant(self, tenant_id):
        """Only the tenant's own tag type groups."""
        return self.filter(tenant_id=tenant_id)

    def list(self, tenant_id, search=None, sort_by="name"):
        query = self.by_tenant(tenant_id)
        if search:
            query = query.filter(name__icontains=search)
        return query.order_by(sort_by)


class TagTypeQuerySet(BaseQuerySet):
    def by_tenant(self, tenant_id):
        """Only the tenant's own tag types."""
        return self.filter(tenant_id=tenant_id)

    def list(self, tenant_id, search=None, group=None, sort_by="name"):
        query = self.by_tenant(tenant_id).select_related("group").prefetch_related("tag_ranges")
        if search:
            query = query.filter(name__icontains=search)
        if group:
            query = query.filter(group_id=group)
        return query.order_by(sort_by)

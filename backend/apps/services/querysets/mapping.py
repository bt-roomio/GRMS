from core.querysets.base_queryset import BaseQuerySet


class MappingProfileQuerySet(BaseQuerySet):
    def by_tenant(self, tenant_id):
        """Only the tenant's own mapping profiles."""
        return self.filter(tenant_id=tenant_id)

    def with_rules(self):
        return self.prefetch_related("rules__tag_type")

    def list(self, tenant_id, search=None, integrator=None, sort_by="code"):
        query = self.by_tenant(tenant_id).with_rules()
        if search:
            query = query.filter(name__icontains=search)
        if integrator:
            query = query.filter(integrator_id=integrator)
        return query.order_by(sort_by)


class MappingOverrideQuerySet(BaseQuerySet):
    def by_tenant(self, tenant_id):
        """Overrides of the tenant's own integrations."""
        return self.filter(integration__tenant_id=tenant_id)

    def list(self, tenant_id, integration=None, level=None):
        query = self.by_tenant(tenant_id)
        if integration:
            query = query.filter(integration_id=integration)
        if level:
            query = query.filter(level=level)
        return query.order_by("integration_id", "level", "created_at")

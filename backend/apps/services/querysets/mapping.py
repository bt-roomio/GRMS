from core.querysets.base_queryset import BaseQuerySet


class MappingProfileQuerySet(BaseQuerySet):
    def by_tenant(self, tenant_id):
        """Only the tenant's own mapping profiles."""
        return self.filter(tenant_id=tenant_id)

    def with_rules(self):
        return self.prefetch_related("rules", "integrations", "room_types", "devices")

    def list(self, tenant_id, search=None, integrator=None, scope=None, room_type=None, device=None, sort_by="name"):
        query = self.by_tenant(tenant_id).with_rules()
        if search:
            query = query.filter(name__icontains=search)
        if integrator:
            query = query.filter(integrator_id=integrator)
        if scope:
            query = query.filter(scope=scope)
        if room_type:
            query = query.filter(room_types=room_type)
        if device:
            query = query.filter(devices=device)
        return query.order_by(sort_by)

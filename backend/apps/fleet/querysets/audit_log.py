from core.querysets.base_queryset import BaseQuerySet


class FleetAuditLogQuerySet(BaseQuerySet):
    def for_node(self, node_id):
        return self.filter(node_id=node_id).select_related("user")

    def for_tenant(self, tenant_id):
        if tenant_id is None:
            return self
        return self.filter(node__tenant_id=tenant_id)

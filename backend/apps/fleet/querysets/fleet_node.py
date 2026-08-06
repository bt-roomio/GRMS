from django.db.models import Q

from rest_framework.generics import get_object_or_404

from core.querysets.base_queryset import BaseQuerySet


class FleetNodeQuerySet(BaseQuerySet):
    def is_active(self):
        return self.filter(is_active=True)

    def online(self):
        return self.is_active().filter(is_online=True)

    def for_tenant(self, tenant_id):
        """Superusers pass ``tenant_id=None`` to see the whole fleet."""
        if tenant_id is None:
            return self
        return self.filter(tenant_id=tenant_id)

    def list(self, tenant_id, sort_by=None, search_value=None, is_online=None, node_id=None):
        query = self.is_active().for_tenant(tenant_id).select_related("tenant", "gateway")

        if node_id:
            query = query.filter(id=node_id)

        if search_value:
            query = query.filter(
                Q(code__icontains=search_value)
                | Q(title__icontains=search_value)
                | Q(mesh_ip__icontains=search_value)
                | Q(gateway__name__icontains=search_value)
            )

        if is_online is not None:
            query = query.filter(is_online=is_online)

        return query.order_by(*sort_by or ["code"])

    def get_node(self, node_id, tenant_id):
        return get_object_or_404(self.is_active().for_tenant(tenant_id), pk=node_id)

    def for_gateway(self, gateway_id):
        return self.is_active().filter(gateway_id=gateway_id).first()

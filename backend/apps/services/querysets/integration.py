from django.db.models import Q

from core.querysets.base_queryset import BaseQuerySet


class IntegrationQuerySet(BaseQuerySet):
    def list(self, tenant_id, sort_by=None, search_field=None, search_value=None):
        query = self.filter(tenant_id=tenant_id, is_active=True, enable=True)
        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))
        if sort_by:
            query = query.order_by(*sort_by) if sort_by else query
        return query

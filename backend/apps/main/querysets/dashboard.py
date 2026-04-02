from django.db.models import Q

from core.querysets.base_queryset import BaseQuerySet


class DashboardQuerySet(BaseQuerySet):
    def list(self, tenant_id, search_field=None, search_value=None, sort_by=None):
        query = self.prefetch_related("room_types").filter(tenant_id=tenant_id)
        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))
        elif search_value:
            query = query.filter(Q(title__istartswith=search_value))
        query = query.order_by(*sort_by) if sort_by else query

        return query

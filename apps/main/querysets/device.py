from django.db.models import Q

from core.querysets.base_queryset import BaseQuerySet


class DeviceQuerySet(BaseQuerySet):
    def list(self, tenant, search_field=None, search_value=None, status=None, sort_by=None):
        query = self.select_related("credentials").filter(tenant=tenant, is_active=True)
        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__startswith": search_value}))
        query = query.filter(status=status) if status is not None else query
        query = query.order_by(*sort_by) if sort_by else query

        return query

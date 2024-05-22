from django.db.models import Q
from core.querysets.base_queryset import BaseQuerySet


class RoomQuerySet(BaseQuerySet):
    def list(self, tenant, status, search_field=None, search_value=None, sort_by=None):
        query = self.filter(active=True)
        query = query.filter(status=status, tenant=tenant)
        query = (
            query.filter(Q(**{f"{search_field}__startswith": search_value})) if search_field and search_value else query
        )
        query = query.order_by(*sort_by) if sort_by else query
        return query

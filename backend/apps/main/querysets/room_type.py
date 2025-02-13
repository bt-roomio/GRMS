from django.db.models import Q

from core.querysets.base_queryset import BaseQuerySet


class RoomTypeQuerySet(BaseQuerySet):
    def list(self, tenant, search_field=None, search_value=None, search=None):
        query = self.filter(tenant=tenant)
        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))

        return query.order_by("created_at")

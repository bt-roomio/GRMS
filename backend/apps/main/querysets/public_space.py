from django.db.models import Q

from core.querysets.base_queryset import BaseQuerySet


class PublicSpaceQuerySet(BaseQuerySet):
    def list(self, tenant_id, sort_by=None, search_field=None, search_value=None, accessible_for_guest=None):
        query = self.select_related("created_by").filter(tenant_id=tenant_id)

        if accessible_for_guest is not None:
            query = self.filter(accessible_for_guest=accessible_for_guest)

        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))

        return query.order_by(*sort_by)

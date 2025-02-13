from django.db.models import Q

from core.querysets.base_queryset import BaseQuerySet


class StaffQuerySet(BaseQuerySet):
    def list(self, tenant_id, sort_by=None, search_field=None, search_value=None):
        query = self.select_related("created_by").filter(tenant_id=tenant_id).is_active()

        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))

        return query.order_by(*sort_by)

    def is_active(self):
        return self.filter(is_active=True)

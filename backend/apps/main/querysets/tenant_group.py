from django.db.models import Count, Q

from core.querysets.base_queryset import BaseQuerySet


class TenantGroupQuerySet(BaseQuerySet):
    def list(self, sort_by=None, search_field=None, search_value=None):
        query = self.count_tenants()

        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))

        return query.order_by(*sort_by) if sort_by else query.order_by("-created_at")

    def count_tenants(self):
        return self.annotate(tenants_count=Count("tenants"))

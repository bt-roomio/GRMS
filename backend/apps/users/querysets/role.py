from django.db.models import Q, QuerySet


class RoleQuerySet(QuerySet):
    def list(self, tenants, unscoped, search_field=None, search_value=None):
        """`tenants` is the caller's scope; `unscoped` lifts it for a plain superuser."""
        query = self.prefetch_related("permissions")
        query = query if unscoped else query.filter(tenant__in=tenants)
        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))
        elif search_value:
            query = query.filter(Q(name__istartswith=search_value))
        return query

    def quick_list(self, tenant, search_value=None):
        query = self.filter(tenant=tenant)
        if search_value:
            query = query.filter(Q(name__icontains=search_value))
        return query

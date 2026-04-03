from django.db.models import Q, QuerySet


class RoleQuerySet(QuerySet):
    def list(self, tenant, is_superuser, search_field=None, search_value=None):
        query = self.prefetch_related("permissions")
        query = query.filter(tenant=tenant) if not is_superuser else query
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

from django.db.models import QuerySet


class RoleQuerySet(QuerySet):
    def list(self, tenant, is_superuser):
        query = self.prefetch_related("permissions")
        query = query.filter(tenant=tenant) if not is_superuser else query
        return query

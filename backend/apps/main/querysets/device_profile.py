from django.db.models import Q

from core.querysets.base_queryset import BaseQuerySet


class DeviceProfileQuerySet(BaseQuerySet):
    def list(self, tenant, state=None, search_field=None, search_value=None):
        query = self.filter(tenant=tenant)
        query = query.filter(state=state) if state is not None else query
        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__startswith": search_value}))
        return query

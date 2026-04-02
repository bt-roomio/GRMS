from django.db.models import Q

from core.querysets.base_queryset import BaseQuerySet


class GuestQuerySet(BaseQuerySet):
    def list(self, tenant_id, room=None, sort_by=[], search_field=None, search_value=None):
        query = self.filter(tenant_id=tenant_id, is_active=True)
        query = query.filter(room=room) if room else query
        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))
        elif search_value:
            query = query.filter(
                Q(name__istartswith=search_value) | Q(lastname__istartswith=search_value) | Q(gender__istartswith=search_value)
            )
        return query.order_by(*sort_by)

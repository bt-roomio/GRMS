from django.db.models import Q

from core.querysets.base_queryset import BaseQuerySet


class GuestQuerySet(BaseQuerySet):
    def list(self, tenant_id, room=None, room_state=None, sort_by=[], search_field=None, search_value=None):
        from main.models import Room

        query = self.filter(tenant_id=tenant_id, is_active=True)
        query = query.filter(room=room) if room else query

        if room_state and room_state == Room.CheckedIn:
            query = query.filter(is_active=True, is_reservation=False)
        if room_state and room_state == Room.Reserved:
            query = query.filter(is_active=True, is_reservation=True)

        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))
        elif search_value:
            query = query.filter(
                Q(name__istartswith=search_value)
                | Q(lastname__istartswith=search_value)
                | Q(gender__istartswith=search_value)
            )

        return query.order_by(*sort_by)

    def quick_list(self, tenant_id, room=None, search_value=None):
        query = self.filter(tenant_id=tenant_id, is_active=True)
        if search_value:
            query = query.filter(
                Q(name__icontains=search_value)
                | Q(lastname__icontains=search_value)
                | Q(gender__icontains=search_value)
            )
        query = query.filter(room=room) if room else query
        return query

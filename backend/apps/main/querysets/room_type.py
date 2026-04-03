from django.db.models import Prefetch, Q

from core.querysets.base_queryset import BaseQuerySet


class RoomTypeQuerySet(BaseQuerySet):
    def list(self, tenant, search_field=None, search_value=None):
        query = self.filter(tenant=tenant).prefetch_related(
            Prefetch(
                "room_type_public_spaces__room_type",
                queryset=None,
                to_attr="prefetched_public_spaces",
            )
        )
        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))
        elif search_value:
            query = query.filter(Q(title__istartswith=search_value))

        return query.order_by("created_at")

    def quick_list(self, tenant, search_value=None):
        query = self.filter(tenant=tenant)
        if search_value:
            query = query.filter(Q(title__icontains=search_value))
        return query

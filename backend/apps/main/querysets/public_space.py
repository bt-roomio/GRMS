from django.db.models import Prefetch, Q

from core.querysets.base_queryset import BaseQuerySet


class PublicSpaceQuerySet(BaseQuerySet):
    def list(self, tenant_id, sort_by=None, search_field=None, search_value=None, accessible_for_guest=None):
        from main.models import DevicePublicSpaces

        sort_by = sort_by or ["created_at"]

        query = (
            self.select_related("created_by")
            .prefetch_related(
                Prefetch(
                    "device_public_spaces",
                    queryset=DevicePublicSpaces.objects.select_related(
                        "device__device_profile", "device__credentials", "device__room"
                    ),
                    to_attr="prefetched_devices",
                )
            )
            .filter(tenant_id=tenant_id)
        )

        if accessible_for_guest is not None:
            query = self.filter(accessible_for_guest=accessible_for_guest)

        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))
        elif search_value:
            query = query.filter(Q(name__istartswith=search_value))

        return query.order_by(*sort_by)

    def quick_list(self, tenant_id, search_value=None):
        query = self.filter(tenant_id=tenant_id)
        if search_value:
            query = query.filter(Q(name__icontains=search_value))
        return query


class DevicePublicSpacesQuerySet(BaseQuerySet):
    pass


class RoomTypePublicSpacesQuerySet(BaseQuerySet):
    pass

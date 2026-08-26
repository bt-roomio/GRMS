from django.db.models import Count, Q

from core.querysets.base_queryset import BaseQuerySet


class TenantQuerySet(BaseQuerySet):
    def list(self, sort_by=None, search_field=None, search_value=None, group=None):
        # `group_title` is serialised for every row, so the chain comes along in one join.
        query = self.select_related("group").count_devices()

        if group:
            query = query.filter(group_id=group)
        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))
        if sort_by:
            query = query.order_by(*sort_by) if sort_by else query.order_by("created_at")

        return query

    def count_devices(self):
        query = self.annotate(
            online_rooms=Count(
                "device",
                filter=Q(device__is_active=True, device__room__isnull=False, device__status=True),
            ),
            offline_rooms=Count(
                "device",
                filter=Q(device__is_active=True, device__room__isnull=False, device__status=False),
            ),
            total_rooms=Count(
                "device",
                filter=Q(device__is_active=True, device__room__isnull=False),
            ),
            offline_gateways=Count(
                "device",
                filter=Q(device__is_active=True, device__additional_info__gateway=True, device__status=False),
            ),
            total_gateways=Count(
                "device",
                filter=Q(device__is_active=True, device__additional_info__gateway=True),
            ),
        )
        return query

from django.db.models import BooleanField, Case, Exists, OuterRef, Prefetch, Q, Subquery, Value, When

from core.querysets.base_queryset import BaseQuerySet


class PublicSpaceQuerySet(BaseQuerySet):
    def with_status(self):
        from main.models import DevicePublicSpaces

        has_devices = Exists(DevicePublicSpaces.objects.filter(public_space=OuterRef("pk")))
        has_offline_devices = Exists(
            DevicePublicSpaces.objects.filter(public_space=OuterRef("pk"), device__status=False)
        )
        return self.annotate(
            _has_devices=has_devices,
            _has_offline_devices=has_offline_devices,
        ).annotate(
            status=Case(
                When(_has_devices=True, _has_offline_devices=False, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )

    def list(
        self, tenant_id, sort_by=None, search_field=None, search_value=None, accessible_for_guest=None, status=None
    ):
        from main.models import DevicePublicSpaces

        sort_by = sort_by or ["created_at"]

        query = (
            self.with_status()
            .select_related("created_by")
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
            query = query.filter(accessible_for_guest=accessible_for_guest)

        if status is not None:
            query = query.filter(status=status)

        if search_field == "device_name" and search_value:
            query = query.filter(device_public_spaces__device__name__icontains=search_value).distinct()
        elif search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))
        elif search_value:
            query = query.filter(Q(name__istartswith=search_value))

        return query.order_by(*sort_by)

    def door_lock_devices(self):
        from main.models import DevicePublicSpaces

        first_device = DevicePublicSpaces.objects.filter(public_space=OuterRef("pk"), device__is_active=True).order_by(
            "device__created_at"
        )

        return self.annotate(
            effective_device_id=Subquery(first_device.values("device_id")[:1]),
            effective_device_status=Subquery(first_device.values("device__status")[:1], output_field=BooleanField()),
        ).filter(effective_device_id__isnull=False)

    def quick_list(self, tenant_id, search_value=None):
        query = self.filter(tenant_id=tenant_id)
        if search_value:
            query = query.filter(Q(name__icontains=search_value))
        return query


class DevicePublicSpacesQuerySet(BaseQuerySet):
    pass


class RoomTypePublicSpacesQuerySet(BaseQuerySet):
    pass

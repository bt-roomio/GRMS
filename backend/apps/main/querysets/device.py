from access_manager.models import NeedSyncDevice
from django.db.models import Case, Exists, OuterRef, Prefetch, Q, Value, When
from django.db.models.fields import IntegerField

from core.querysets.base_queryset import BaseQuerySet


class DeviceQuerySet(BaseQuerySet):
    def quick_list(self, tenant, search_value=None, device_profile=None):
        query = self.select_related("credentials", "device_profile").filter(tenant=tenant, is_active=True)
        query = query.filter(device_profile__name=device_profile) if device_profile else query
        if search_value:
            query = query.filter(Q(name__istartswith=search_value) | Q(label__istartswith=search_value))
        return query

    def list(
        self, tenant, search_field=None, search_value=None, status=None, sort_by=None, name=None, device_profile=None
    ):
        query = (
            self.select_related("credentials", "device_profile")
            .prefetch_related("device_public_spaces__public_space")
            .filter(tenant=tenant, is_active=True)
        )
        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))
        elif search_value:
            query = query.filter(
                Q(name__istartswith=search_value)
                | Q(device_profile__name__istartswith=search_value)
                | Q(label__istartswith=search_value)
            )
        if name:
            query = query.filter(
                Q(name__istartswith=name)
                | Q(room__number__istartswith=name)
                | Q(device_public_spaces__public_space__name__istartswith=name)
            ).distinct()

        query = query.filter(status=status) if status is not None else query
        if device_profile is not None:
            query = query.filter(device_profile_id=device_profile)

        if sort_by:
            has_gateway_sort = any(f in ("gateway", "-gateway") for f in sort_by)
            if has_gateway_sort:
                query = query.annotate(
                    _is_gateway=Case(
                        When(additional_info__gateway=True, then=Value(0)),
                        default=Value(1),
                        output_field=IntegerField(),
                    )
                )

            sort_map = {
                "device_profile": "device_profile__name",
                "-device_profile": "-device_profile__name",
                "gateway": "_is_gateway",
                "-gateway": "-_is_gateway",
            }
            query = query.order_by(*(sort_map.get(f, f) for f in sort_by))

        return query

    def gateway_or_none(self, pk):
        return self.filter(pk=pk, additional_info__gateway=True, is_active=True).first()

    def active_inactive(self, public_space_id, tenant):
        device_objects = self.filter(
            device_public_spaces__public_space__id=public_space_id, tenant=tenant, is_active=True
        ).distinct()
        active_devices = device_objects.filter(status=True)
        inactive_devices = device_objects.filter(status=False)

        return active_devices, inactive_devices

    def is_active(self):
        return self.filter(is_active=True)

    def find_device_by_room(self, room):
        return self.is_active().filter(room=room).order_by("created_at").first()

    def get_relation_or_gateway(self, pk):
        from shuttle.models import Relation

        relation = Relation.objects.filter(to_id_id=pk).first()
        from_id = relation and relation.from_id.id
        gateway = self.gateway_or_none(pk)

        if from_id is not None:
            return from_id
        elif gateway:
            return gateway.id

        return pk

    def emergency_status(self, tenant_id, room_types, delisting_devices, devices):
        query = self.select_related("room__type").filter(tenant=tenant_id)
        query = query.filter(room__type__title__in=room_types) if room_types else query
        query = query.filter(id__in=devices) if devices else query
        query = query.exclude(id__in=delisting_devices) if delisting_devices else query
        return query

    def get_card_related_devices(self, card, need_sync=None):
        from access_manager.models import GuestCard, StaffCard
        from main.models import DevicePublicSpaces, PublicSpace, Room

        card_id, tenant_id = card.id, card.tenant_id

        staff_ids = list(
            StaffCard.objects.filter(
                card_id=card_id, is_active=True, staff__is_active=True,
            ).values_list("staff_id", flat=True)
        )
        guest_ids = list(
            GuestCard.objects.filter(
                card_id=card_id, is_active=True, guest__is_active=True,
            ).values_list("guest_id", flat=True)
        )

        room_q = Q()
        if staff_ids:
            room_q |= Q(
                group_room__group__staff__id__in=staff_ids,
                group_room__group__is_active=True,
            )
        if guest_ids:
            room_q |= Q(guests__id__in=guest_ids)

        door_lock_device_ids: set = set()
        open_room_ids: set = set()
        if room_q:
            for rid, dlock in (
                Room.objects.filter(room_q, tenant_id=tenant_id)
                .values_list("id", "door_lock_device_id")
                .distinct()
            ):
                if dlock:
                    door_lock_device_ids.add(dlock)
                else:
                    open_room_ids.add(rid)

        ps_q = Q()
        if staff_ids:
            ps_q |= Q(
                group_public_space__group__staff__id__in=staff_ids,
                group_public_space__group__is_active=True,
            )
        if guest_ids:
            ps_q |= (
                Q(guestpublicspace__guest_id__in=guest_ids)
                | Q(room_type_public_spaces__room_type__room__guests__id__in=guest_ids)
            )

        public_space_device_ids: set = set()
        if ps_q:
            public_space_ids = list(
                PublicSpace.objects.filter(ps_q, tenant_id=tenant_id)
                .values_list("id", flat=True)
                .distinct()
            )
            if public_space_ids:
                public_space_device_ids = set(
                    DevicePublicSpaces.objects
                    .filter(public_space_id__in=public_space_ids)
                    .values_list("device_id", flat=True)
                    .distinct()
                )


        queued_device_ids = set(
            NeedSyncDevice.objects
            .filter(card_id=card_id, need_sync=True)
            .values_list("device_id", flat=True)
            .distinct()
        )

        matched_ids = door_lock_device_ids | public_space_device_ids | queued_device_ids
        if not matched_ids and not open_room_ids:
            return self.none()

        qs = (
            self.filter(is_active=True, tenant_id=tenant_id)
            .filter(Q(id__in=matched_ids) | Q(room_id__in=open_room_ids))
            .select_related("room", "as_door_lock_room")
            .prefetch_related(
                Prefetch(
                    "device_public_spaces",
                    queryset=DevicePublicSpaces.objects.select_related("public_space"),
                    to_attr="prefetched_device_public_spaces",
                )
            )
            .annotate(
                need_sync=Exists(
                    NeedSyncDevice.objects.filter(
                        device=OuterRef("pk"), card_id=card_id, need_sync=True,
                    )
                )
            )
        )

        if need_sync is not None:
            qs = qs.filter(need_sync=need_sync)

        return qs

    def offline_count(self, tenant_id):
        offline_rooms = (
            self.filter(tenant_id=tenant_id, is_active=True, room__isnull=False, status=False)
            .values_list("id", flat=True)
            .distinct()
            .count()
        )

        return offline_rooms

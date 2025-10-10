from django.db.models import Q, Exists, OuterRef, Prefetch

from access_manager.models import NeedSyncDevice
from core.querysets.base_queryset import BaseQuerySet


class DeviceQuerySet(BaseQuerySet):
    def list(self, tenant, search_field=None, search_value=None, status=None, sort_by=None):
        query = self.select_related("credentials", "device_profile").filter(tenant=tenant, is_active=True)
        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))
        query = query.filter(status=status) if status is not None else query
        query = query.order_by(*sort_by) if sort_by else query

        return query

    def gateway_or_none(self, pk):
        return self.filter(pk=pk, additional_info__gateway=True, is_active=True).first()

    def active_inactive(self, public_space_id, tenant):
        device_objects = self.filter(
            device_public_spaces__public_space__id=public_space_id,
            tenant=tenant,
            is_active=True
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

    def get_card_related_devices(self, card_id, need_sync=None):
        from main.models import DevicePublicSpaces
        qs = self.select_related("tenant", "room").prefetch_related(
            Prefetch(
                "device_public_spaces",
                queryset=DevicePublicSpaces.objects.select_related("public_space"),
                to_attr="prefetched_device_public_spaces",
            )
        ).filter(
            Q(room__group_room__group__staff__staffcard__card=card_id,
              room__group_room__group__staff__staffcard__is_active=True) |

            Q(device_public_spaces__public_space__group_public_space__group__staff__staffcard__card=card_id,
              device_public_spaces__public_space__group_public_space__group__staff__staffcard__is_active=True, ) |

            Q(room__guests__guestcard__card=card_id,
              room__guests__guestcard__is_active=True) |

            Q(device_public_spaces__public_space__guestpublicspace__guest__guestcard__card=card_id,
              device_public_spaces__public_space__guestpublicspace__guest__guestcard__is_active=True) |

            Q(needsyncdevice__card=card_id,
              needsyncdevice__need_sync=True)
        ).annotate(
            need_sync=Exists(
                NeedSyncDevice.objects.filter(
                    device=OuterRef('pk'),
                    card=card_id,
                    need_sync=True
                )
            )
        ).distinct()

        if need_sync is not None:
            qs = qs.filter(need_sync=need_sync)

        return qs

    def offline_count(self, tenant_id):
        offline_rooms = self.filter(tenant_id=tenant_id, is_active=True, room__isnull=False, status=False).values_list(
            "id", flat=True).distinct().count()

        return offline_rooms

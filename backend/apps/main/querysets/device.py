from django.db.models import Q

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

    def emergency_status(self, tenant_id, room_types, delisting_devices):
        query = self.select_related("room__type").filter(tenant=tenant_id)
        query = query.filter(room__type__title__in=room_types) if room_types else query
        query = query.exclude(id__in=delisting_devices) if delisting_devices else query
        return query

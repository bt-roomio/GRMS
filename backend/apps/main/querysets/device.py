from django.db.models import Q

from core.querysets.base_queryset import BaseQuerySet


class DeviceQuerySet(BaseQuerySet):
    def list(self, tenant, search_field=None, search_value=None, status=None, sort_by=None):
        query = self.select_related("credentials", "device_profile").filter(tenant=tenant, is_active=True)
        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__startswith": search_value}))
        query = query.filter(status=status) if status is not None else query
        query = query.order_by(*sort_by) if sort_by else query

        return query

    def gateway_or_none(self, pk):
        return self.filter(pk=pk, additional_info__gateway=True, is_active=True).first()

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

from django.db.models import Q

from core.querysets.base_queryset import BaseQuerySet


class CardLogQuerySet(BaseQuerySet):
    def by_room(self, room_id):
        return self.filter(device__room__id=room_id, device__is_active=True)

    def by_public_space(self, public_space_id):
        return self.filter(device__device_public_spaces__public_space=public_space_id, device__is_active=True)

    def by_user(self, user_id):
        return self.filter(Q(guest_id=user_id) | Q(staff_id=user_id))

    def by_card_num(self, card_number, tenant):
        return self.filter(number=card_number, tenant=tenant)

    def list(self, tenant_id=None, filters={}, device_ids=None, sort_by=None, user_id=None, card_num=None, tenant=None,
             room_id=None, public_space_id=None, room_ids=None, public_space_ids=None):
        query = self
        from_date = filters.get("from_date")
        to_date = filters.get("to_date")

        if tenant_id:
            query = self.filter(device__tenant_id=tenant_id)
        if from_date:
            query = query.filter(event_ts__gte=from_date)
        if to_date:
            query = query.filter(event_ts__lte=to_date)

        if device_ids:
            query = query.filter(device_id__in=device_ids)

        room_ids = (room_ids or []) + ([room_id] if room_id else [])
        public_space_ids = (public_space_ids or []) + ([public_space_id] if public_space_id else [])

        if room_ids or public_space_ids:
            query = query.filter(
                Q(device__room__id__in=room_ids, device__is_active=True) |
                Q(device__device_public_spaces__public_space__in=public_space_ids, device__is_active=True)
            )

        if user_id:
            query = query.by_user(user_id)
        if card_num and tenant:
            query = query.by_card_num(card_num, tenant)

        return query.order_by(*sort_by)

from django.db.models import Count, Q

from core.querysets.base_queryset import BaseQuerySet


class GroupQuerySet(BaseQuerySet):
    def list(self, tenant_id, sort_by=None, search_field=None, search_value=None):
        query = (
            self.prefetch_related("group_room", "created_by", "group_public_space")
            .filter(tenant_id=tenant_id)
            .is_active()
        )

        query = query.annotate(count_staff=Count("staff"))

        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))

        return query.order_by(*sort_by)

    def is_active(self):
        return self.filter(is_active=True)

    def get_staff_cards(self, group_id):
        from access_manager.models import StaffCard
        group = self.filter(id=group_id, is_active=True).first()

        if not group:
            return None, None

        staff_cards = StaffCard.objects.filter(
            staff__group=group,
            staff__is_active=True,
            is_active=True
        ).select_related('card', 'staff')

        if not staff_cards.exists():
            return None, group

        cards = [staff_card.card.number for staff_card in staff_cards]
        return cards, group


class GroupRoomQuerySet(BaseQuerySet):
    pass

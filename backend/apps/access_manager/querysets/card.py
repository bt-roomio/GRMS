from django.db.models import Q, Exists, OuterRef

from core.querysets.base_queryset import BaseQuerySet


class CardQuerySet(BaseQuerySet):
    def list(self, tenant_id, sort_by=None, search_field=None, search_value=None, filters={}, staff_id=None):
        from access_manager.models import NeedSyncDevice, StaffCard

        query = self.select_related("created_by").filter(tenant_id=tenant_id)

        if staff_id:
            query = query.filter(
                id__in=StaffCard.objects.filter(staff_id=staff_id, is_active=True).values("card_id")
            )

        if 'need_sync' in filters:
            need_sync = filters.get("need_sync")
            query = query.annotate(
                need_sync=Exists(
                    NeedSyncDevice.objects.filter(
                        card=OuterRef('pk'),
                        need_sync=True
                    )
                )
            )
            query = query.filter(need_sync=need_sync)

        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))

        return query.order_by(*sort_by)

    def get_rooms(self, card):
        from access_manager.models import StaffCard, GroupRoom, GuestCard

        staff_card = StaffCard.objects.filter(card=card, is_active=True).first()
        if staff_card and staff_card.staff.group:
            return [gr.room for gr in GroupRoom.objects.filter(group=staff_card.staff.group).select_related('room')]

        guest_card = GuestCard.objects.filter(card=card, is_active=True).first()
        if guest_card and hasattr(guest_card.guest, 'room'):
            return [guest_card.guest.room]

        return []

    def get_public_spaces(self, card):
        from access_manager.models import StaffCard, GroupPublicSpace, GuestCard, GuestPublicSpace

        staff_card = StaffCard.objects.filter(card=card, is_active=True).first()
        if staff_card and staff_card.staff.group:
            return [
                gps.public_space
                for gps in GroupPublicSpace.objects.filter(group=staff_card.staff.group).select_related('public_space')
            ]

        guest_card = GuestCard.objects.filter(card=card, is_active=True).first()
        if guest_card:
            return [
                gps.public_space
                for gps in GuestPublicSpace.objects.filter(guest=guest_card.guest).select_related('public_space')
            ]

        return []
